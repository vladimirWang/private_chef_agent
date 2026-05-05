import os

from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.embeddings import DashScopeEmbeddings
from dotenv import load_dotenv

from app.agents import config_data as config
from app.agents.vector_stores import VectorStoreService

load_dotenv()

def print_prompt(prompt):
    print("-"*10, prompt, "-"*10)
    return prompt
    
class RagService(object):
    def __init__(self):
        self.vector_service = VectorStoreService(
            embedding=DashScopeEmbeddings(model=config.embedding_model)
        )
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "以我提供的已知参考资料为主,简洁和专业地回答问题。参考资料: {context}。"),
            ("user", "请回答用户提问: {input}")
        ])
        # 使用 OpenAI 兼容端点（DASHSCOPE_BASE_URL），避免 ChatTongyi 依赖原生 DASHSCOPE_HTTP_BASE_URL 导致 url error
        self.chat_model = init_chat_model(
            model=config.chat_model_name,
            model_provider="openai",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            streaming=True,
        )
        self.chain = self.__get_chain()

    def __get_chain(self):
        # 获得最终执行链
        retriever = self.vector_service.get_retriever()

        def format_document(docs: list[Document]):
            if not docs:
                return "无相关参考资料"
            print("length: ", len(docs))
            formatted_str = ""
            for doc in docs:
                formatted_str += f"文档片段: {doc.page_content}文档元数据: {doc.metadata}"

            return formatted_str
            
        chain = (
            {
                "input": RunnablePassthrough(), 
                "context": retriever | format_document
             } | self.prompt_template | print_prompt | self.chat_model | StrOutputParser()
        )
        return chain

if __name__ == "__main__":
    # 需自行注入环境，例如：uv run --env-file .env.dev python -m app.agents.rag
    res = RagService().chain.invoke("我体重180斤，尺码推荐")
    print(res)