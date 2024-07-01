from llmtuner import ChatModel
from llmtuner.extras.template import system_text, demonstration
from rag import RAGLLM
import os
import json


def main():
    chat_model = ChatModel()
    pre_text = "Hi, I am an AI assistant can help you to convert source table to target table."
    count = 0
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    embedding_path = os.path.join(cur_dir, 'rag/bert-base-uncased')
    db_path = os.path.join(cur_dir, 'rag/knowledge_base.db')
    index_path = os.path.join(cur_dir, 'rag/faiss_index.idx')
    
    model = RAGLLM(embedding_path, db_path, index_path)
    print(model.ids_texts_map)
    # Query the knowledge base
    results = []
    query = "People ID,Name,Country,Is Male,Age"
    results.extend(model.query_columns(query))
    query = "Church ID,Male ID,Year"
    results.extend(model.query_columns(query))
    
    rag_context = "Here are some examples of potentially relevant information that you can refer to, \
    but the answers you give should rely heavily on the questions that follow."
    for result in results:
        rag_context += json.dumps(result, ensure_ascii=False)
    print(rag_context)
    while True:
        if count>= 5:
            break
        print('-'*40)
        print(pre_text)
        try:
            query = input("\nUser:")
        except Exception:
            raise
        query_info = """
        The database schema are below:
        CREATE TABLE "people" (
        "People ID" int,
        "Name" text,
        "Country" text,
        "Is Male" text,
        "Age" int,
        );
        CREATE TABLE "wedding"(
        "Church ID" int,
        "Male ID" int,
        "Year" int,
        );
        CREATE TABLE "result"(
        "Name" text,
        "Year" int,
        "Age level" text,
        )
        """
        prompt_text = system_text + demonstration + query + query_info
        
        #prompt_text = prompt_text.format(source_table=source_table, target_table=target_table)
        # try:
        #     query = input("\nUser: ")
        # except UnicodeDecodeError:
        #     print("Detected decoding error at the inputs, please set the terminal encoding to utf-8.")
        #     continue
        # except Exception:
        #     raise

        # if query.strip() == "exit":
        #     break

        # if query.strip() == "clear":
        #     history = []
        #     print("History has been removed.")
        #     continue

        print("Assistant: ", end="", flush=True)
        response, length_tuple = chat_model.chat(query=prompt_text, max_new_tokens=1500)
        print(response)
        count += 1

        # response = ""
        # for new_text in chat_model.stream_chat(query, history):
        #     print(new_text, end="", flush=True)
        #     response += new_text
        # print()
        # history = history + [(query, response)]


if __name__ == "__main__":
    main()
