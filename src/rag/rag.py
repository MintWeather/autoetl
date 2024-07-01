import sqlite3
import json
import os
import numpy as np
import faiss
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher

class RAGLLM(object):
    def __init__(self, embedding_path, db_path, index_path):
        self.tokenizer = BertTokenizer.from_pretrained(embedding_path)
        self.model = BertModel.from_pretrained(embedding_path)
        self.db_path = db_path
        self.index_path = index_path
        self.index = None
        self.ids_texts_map = {}

    def get_embeddings(self, texts):
        inputs = self.tokenizer(texts, return_tensors='pt', padding=True, truncation=True, max_length=512)
        outputs = self.model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings

    def build_index(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT schema FROM schemas')
        schemas = [row[0] for row in cursor.fetchall()]
        conn.close()

        schema_embeddings = self.get_embeddings(schemas)
        schema_embeddings_np = schema_embeddings.detach().numpy()
        self.index = faiss.IndexFlatL2(schema_embeddings_np.shape[1])
        self.index.add(schema_embeddings_np)

        self.ids_texts_map = {i: schemas[i] for i in range(len(schemas))}
        
        faiss.write_index(self.index, self.index_path)

    def load_index(self):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, schema FROM schemas')
            rows = cursor.fetchall()
            self.ids_texts_map = {row[0] - 1: row[1] for row in rows}
            conn.close()
        else:
            raise FileNotFoundError(f"Index file {self.index_path} not found.")
    
    def insert_index(self, schema):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(id) FROM schemas')
        max_id_row = cursor.fetchone()
        max_id = max_id_row[0] if max_id_row[0] is not None else 0
        cursor.execute('INSERT INTO schemas (id, table_name, schema) VALUES (?, ?, ?)', (max_id + 1, schema['table_name'], schema['schema']))
        conn.commit()
        # cursor.execute('SELECT id, schema FROM schemas')
        # rows = cursor.fetchall()
        cursor.execute('SELECT last_insert_rowid()')
        new_id = cursor.fetchone()[0] - 1
        conn.close()
        
        # Update FAISS index
        schema_embedding = self.get_embeddings([schema['schema']]).detach().numpy()
        self.index.add(schema_embedding)
        
        self.ids_texts_map[new_id] = schema['schema']
        
        faiss.write_index(self.index, self.index_path)

    def delete_index(self, schema):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, schema FROM schemas WHERE schema = ?', (schema,))
        row = cursor.fetchone()
        if row:
            schema_id, db_schema = row
            if db_schema != schema:
                raise ValueError("Schema mismatch. Cannot delete.")
            
            cursor.execute('DELETE FROM schemas WHERE id = ?', (schema_id,))
            cursor.execute('UPDATE schemas SET id = id - 1 WHERE id > ?', (schema_id,))
            conn.commit()
            
            # Update FAISS index
            cursor.execute('SELECT schema FROM schemas')
            schemas = [row[0] for row in cursor.fetchall()]
            schema_embeddings_np = np.array([self.get_embeddings([s]).detach().numpy() for s in schemas])
            
            self.index = faiss.IndexFlatL2(schema_embeddings_np.shape[2])
            self.index.add(schema_embeddings_np.reshape(-1, schema_embeddings_np.shape[2]))
            faiss.write_index(self.index, self.index_path)
            del self.ids_texts_map[schema_id - 1]
            conn.close()
        else:
            conn.close()
            raise ValueError("Schema not found in database.")

    def query_knowledge_base(self, query):
        if self.index is None and not os.path.exists(self.index_path):
            self.build_index()
        else:
            self.load_index()
        
        query_embedding = self.get_embeddings([query]).detach().numpy()
        D, I = self.index.search(query_embedding, k=2)
        matching_schemas = [self.ids_texts_map[i] for i in I[0]]
        
        query_cols = query.split(":")[1].split(",")
        all_results = []
        
        for schema in matching_schemas:
            schema_cols = schema.split(",")
            similar_columns = self.find_similar_columns(query_cols, schema_cols)
            table_name = self.get_table_name_by_schema(schema)
            pipelines = self.get_pipelines_by_table_name(table_name)
            
            for pipeline in pipelines:
                filtered_operations = [
                    op for op in pipeline["operations"]
                    if any(col in json.dumps(op) for col in [col_pair[1] for col_pair in similar_columns])
                ]
                
                result = {
                    "similar_columns": similar_columns,
                    "pipeline": filtered_operations
                }
                
                all_results.append(result)
        
        return all_results

    def get_table_name_by_schema(self, schema):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT table_name FROM schemas WHERE schema = ?', (schema,))
        table_name = cursor.fetchone()[0]
        conn.close()
        return table_name

    def get_pipelines_by_table_name(self, table_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT pipeline_name, source_tables, operations FROM pipelines')
        rows = cursor.fetchall()
        pipelines = []

        for row in rows:
            pipeline_name, source_tables, operations = row
            source_tables = json.loads(source_tables)
            operations = json.loads(operations)
            if table_name in source_tables:
                pipelines.append({
                    "pipeline_name": pipeline_name,
                    "source_tables": source_tables,
                    "operations": operations
                })
        
        conn.close()
        return pipelines
    
    def find_similar_columns(self, query_cols, schema_cols):
        query_col_embeddings = self.get_embeddings(query_cols).detach().numpy()
        schema_col_embeddings = self.get_embeddings(schema_cols).detach().numpy()       
        similarities = cosine_similarity(query_col_embeddings, schema_col_embeddings)     
        # max_similarities = similarities.max(axis=1)
        best_matches = similarities.argmax(axis=1)      
        similar_columns = [(query_cols[i], schema_cols[best_matches[i]]) for i in range(len(query_cols))]      
        return similar_columns
    
    def find_similar_columns_by_name(self, query_cols, schema_cols, threshold=0.7):
        """
        Find similar columns based on string similarity.

        Parameters:
        - query_cols: List of columns to query.
        - schema_cols: List of columns in the schema.
        - threshold: Similarity threshold for considering columns as similar.

        Returns:
        - List of tuples with similar columns (query_col, schema_col).
        """
        similar_columns = []
        for query_col in query_cols:
            best_match = None
            best_ratio = 0
            for schema_col in schema_cols:
                ratio = SequenceMatcher(None, query_col, schema_col).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = schema_col
            if best_ratio >= threshold:
                similar_columns.append((query_col, best_match))
        return similar_columns

    def query_columns(self, query):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT table_name, schema FROM schemas')
        rows = cursor.fetchall()
        conn.close()

        query_cols = query.split(",")
        all_results = []
        
        for row in rows:
            table_name, schema = row
            schema_cols = schema.split(",")
            similar_columns = self.find_similar_columns_by_name(query_cols, schema_cols)
            if similar_columns:
                pipelines = self.get_pipelines_by_table_name(table_name)
                
                for pipeline in pipelines:
                    filtered_operations = [
                        op for op in pipeline["operations"]
                        if any(col in json.dumps(op) for col in [col_pair[1] for col_pair in similar_columns])
                    ]
                    
                    result = {
                        "similar_columns": similar_columns,
                        "pipeline": filtered_operations
                    }
                    
                    all_results.append(result)
        
        return all_results
def main():
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    embedding_path = os.path.join(cur_dir, 'bert-base-uncased')
    db_path = os.path.join(cur_dir, 'knowledge_base.db')
    index_path = os.path.join(cur_dir, 'faiss_index.idx')
    
    model = RAGLLM(embedding_path, db_path, index_path)
    print(model.ids_texts_map)
    # Query the knowledge base
    query = "order_id,customer_id,amount,status"
    matching_schemas = model.query_columns(query)
    
    # 输出结果
    for result in matching_schemas:
        print(json.dumps(result, ensure_ascii=False, indent=4))

    # 
    # new_schema = {
    #     'table_name': 'new_table',
    #     'schema': 'new_id, new_column1, new_column2'
    # }
    # model.insert_index(new_schema)
    # print(model.ids_texts_map)
    # 
    # schema_to_delete = 'new_id, new_column1, new_column2'
    # model.delete_index(schema_to_delete)
    # print(model.ids_texts_map)
if __name__ == '__main__':
    main()
