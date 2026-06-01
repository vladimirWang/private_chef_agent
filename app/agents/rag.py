from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory

import app.agents.config_data as config
from app.agents.sqlalchemy_history_store import get_rag_history
from app.agents.vector_stores import VectorStore


def print_prompt(prompt: PromptValue):
    print("---------以下为提示词---------")
    print(prompt)
    return prompt


class RagService(object):
    def __init__(self):
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是尺码咨询助手。回答必须严格依据下方【参考资料】，不得编造参考资料中未出现的尺码或区间。"
                    "若参考资料为「无相关参考资料」，请明确告知用户知识库暂无匹配信息，不要猜测或使用通用尺码表。"
                    "忽略对话历史中可能存在的过时 assistant 回答。\n\n【参考资料】\n{context}",
                ),
                MessagesPlaceholder("history"),
                ("human", "{input}"),
            ],
        )
        self.chat_model = ChatTongyi(model=config.chat_model_name)
        self.vector_store = VectorStore()
        self.chain = self.__get_chain()

    def __get_chain(self):
        retriever = self.vector_store.get_retriever()

        def format_func(docs: list[Document]):
            print("------format_func-------", type(docs), len(docs))
            if not docs:
                return "无相关参考资料"
            # print("func_format: ", len(docs))
            result = "".join(doc.page_content for doc in docs)
            print("format_func result: ", result)
            return f"[{result}]"

        def format_for_retriever(value):
            return value["input"]

        def format_prompt(value):
            # print("format_prompt value: ", value)
            return {
                "input": value["input"]["input"],
                "history": value["input"]["history"],
                "context": value["context"],
            }

        chain = (
            {
                "input": RunnablePassthrough(),
                "context": RunnableLambda(format_for_retriever)
                | retriever
                | RunnableLambda(format_func),
            }
            | RunnableLambda(format_prompt)
            # | RunnableLambda(print_prompt)
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )

        conversation_chain = RunnableWithMessageHistory(
            chain,
            get_rag_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        return conversation_chain

if __name__ == "__main__":
    rag = RagService()
    session_config = {"configurable": {"session_id": "user_1"}}
    result = rag.chain.invoke({"input": "什么是RAG？"}, session_config)
    print("最终结果.length: ", type(result), len(result))
    # for message in result['messages']:
    #     print("遍历输出: ", message['role'], message['content'])