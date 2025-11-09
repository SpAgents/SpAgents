import sqlite3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os

class LongTermMemory:
    def __init__(self, db_path="vector_database.db", model_name="emilyalsentzer/Bio_ClinicalBERT"):
        self.db_path = db_path
        self.model = SentenceTransformer(model_name)
        self.vector_dim = self.model.get_sentence_embedding_dimension()
        
        # 初始化数据库
        self._initialize_database()
        self._load_vectors()
    
    def _initialize_database(self):
        """初始化 SQLite 数据库"""
        dir_path = os.path.dirname(self.db_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vectors (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            medical_record TEXT,
                            diagnosis TEXT,
                            record_vector BLOB,
                            diagnosis_vector BLOB)''')
        conn.commit()
        conn.close()
    
    def _load_vectors(self):
        """加载数据库中的向量到 FAISS"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, record_vector FROM vectors")
        vectors = cursor.fetchall()
        conn.close()

        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.id_map = []  # 用于存储数据库的 id 映射

        if vectors:
            vector_list = []
            for row in vectors:
                db_id, vec_blob = row
                vector = np.frombuffer(vec_blob, dtype=np.float32)
                vector_list.append(vector)
                self.id_map.append(db_id)  # 记录数据库的 id
            
            if vector_list:
                self.index.add(np.array(vector_list))
    
    def add_entry(self, medical_record, diagnosis):
        """向数据库中添加病历及其诊断"""
        record_vector = self.model.encode(medical_record).astype(np.float32)
        diagnosis_vector = self.model.encode(diagnosis).astype(np.float32)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO vectors (medical_record, diagnosis, record_vector, diagnosis_vector) VALUES (?, ?, ?, ?)", 
                       (medical_record, diagnosis, record_vector.tobytes(), diagnosis_vector.tobytes()))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        self.index.add(np.array([record_vector]))
        self.id_map.append(new_id)
    
    def delete_entry(self, medical_record):
        """删除指定病历及其相关信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vectors WHERE medical_record = ?", (medical_record,))
        conn.commit()
        conn.close()
        self._reload_index()
    
    def _reload_index(self):
        """重新加载 FAISS 索引"""
        self._load_vectors()
    
    def search(self, query, k=5):
        """根据病历搜索最相近的 k 个病历及其诊断"""
        query_vector = self.model.encode(query).astype(np.float32)
        distances, indices = self.index.search(np.array([query_vector]), k)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = []
        for idx in indices[0]:
            if idx == -1 or idx >= len(self.id_map):
                continue
            db_id = self.id_map[idx]  # 获取数据库中的 id
            cursor.execute("SELECT medical_record, diagnosis FROM vectors WHERE id = ?", (db_id,))
            result = cursor.fetchone()
            if result:
                results.append({"medical_record": result[0], "diagnosis": result[1]})

        conn.close()
        return results
    
    def get_ref_case(self,query, k=5):
        results = self.search(query, k)
        text = ""
        for i in range(len(results)):
            medical_record = results[i]["medical_record"]
            diagnosis = results[i]["diagnosis"]
            text += "案例参考 {}: \n病人信息: {}\n诊断结果: {}\n\n".format(i+1, medical_record, diagnosis)
        return text
    
    def list_all(self):
        """列出数据库中所有的病历及诊断"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT medical_record, diagnosis FROM vectors")
        all_entries = [{"medical_record": row[0], "diagnosis": row[1]} for row in cursor.fetchall()]
        conn.close()
        return all_entries