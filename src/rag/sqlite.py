import sqlite3
import json

def create_and_populate_db(db_path, knowledge_base):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS schemas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT,
        schema TEXT
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pipelines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pipeline_name TEXT,
        source_tables TEXT,
        operations TEXT
    )''')

    for table_name, schema in knowledge_base['schemas'].items():
        cursor.execute('INSERT INTO schemas (table_name, schema) VALUES (?, ?)', (table_name, schema))
    
    for pipeline_name, pipeline in knowledge_base['pipelines'].items():
        source_tables = list(pipeline['source_tables']) if isinstance(pipeline['source_tables'], set) else pipeline['source_tables']
        operations = pipeline['operations']
        
        for operation in operations:
            if 'groupby' in operation['params'] and isinstance(operation['params']['groupby'], set):
                operation['params']['groupby'] = list(operation['params']['groupby'])

        cursor.execute('INSERT INTO pipelines (pipeline_name, source_tables, operations) VALUES (?, ?, ?)',
                       (pipeline_name, json.dumps(source_tables), json.dumps(operations)))
    
    conn.commit()
    conn.close()

# knowledge_base = {
#     "schemas": {
#         "publication": "Publication_ID,Book_ID,Publisher,Publication_Date,Edition",
#         "author": "Author_ID,Book_ID,Author_Name,Author_Age,Country",
#         "project": "Project_ID,Project_Name,Department,Status",
        
#     },
#     "pipelines": {
#         "pipeline1": {
#             "source_tables": ["bidding_info", "bidding_project"],
#             "operations": [
#                 {"type": "join", "params": {"function_id": "join", "left_table": "employee", "table_id": "project", "join_type": "LEFT_JOIN", "join_keys": [{"condition": "EQUAL", "left_col": "Department", "right_col": "Department"}]}},
#                 {"type": "groupby", "params": {"function_id": "aggregate", "groupby": {"Department"}, "values": [{"function_id": "count", "expression": ["Project_ID"]}]}}
#             ]
#         },
#         "pipeline2": {
#             "source_tables": ["project"],
#             "operations": [
#                 {"type": "case_when", "params": {"function_id": "case_when", "condition_type": "SINGLE_COLUMN", "source_column": "Status", "conditions": [{"operator": "=", "condition": "Completed", "value": 1}, {"operator": "!=", "condition": "Completed", "value": 0}], "target_column": "completed_projects"}},
#                 {"type": "rename", "params": {"function_id": "biz_rename", "rename_type": "special_name", "conditions": [{"source_column": "Project_ID", "target_column": "total_projects"}]}},
#                 {"type": "select", "params": {"function_id": "keep_columns", "column_type": "multiple", "source_columns": ["Department", "total_projects"]}}
#             ]
#         }
#     }
# }
knowledge_base = {
    "schemas": {
        "artist": "Artist_ID,Name,Country,Year_Join,Age",
        "exhibition": "Exhibition_ID,Year,Theme,Artist_ID,Ticket_Price",
        "result": "Name,Year,Theme,Age_Group",
        "employee": "Department,Name,Age",
        "project": "Project_ID,Department,status",
        "Department_Project_Status": "Department,Total_Projects,Completed_Projects,In_Progress_Projects"
    },
    "pipelines": {
        "pipeline1": {
            "source_tables": ["artist", "exhibition"],
            "operations": [
                {
                    "type": "join",
                    "params": {
                        "function_id": "join",
                        "left_table": "artist",
                        "table_id": "exhibition",
                        "join_type": "LEFT_JOIN",
                        "join_keys": [
                            {
                                "condition": "EQUAL",
                                "left_col": "Artist_ID",
                                "right_col": "Artist_ID"
                            }
                        ]
                    }
                },
                {
                    "type": "case_when",
                    "params": {
                        "function_id": "case_when",
                        "condition_type": "SINGLE_COLUMN",
                        "source_column": "Age",
                        "conditions": [
                            {
                                "operator": "<",
                                "condition": "30",
                                "value": "young"
                            },
                            {
                                "operator": ">=",
                                "condition": "30",
                                "value": "Senior"
                            }
                        ],
                        "target_column": "Age_Group"
                    }
                }
            ]
        },
        "pipeline2": {
            "source_tables": ["employee", "project"],
            "operations": [
                {
                    "type": "join",
                    "params": {
                        "function_id": "join",
                        "left_table": "employee",
                        "table_id": "project",
                        "join_type": "LEFT_JOIN",
                        "join_keys": [
                            {
                                "condition": "EQUAL",
                                "left_col": "Department",
                                "right_col": "Department"
                            }
                        ]
                    }
                },
                {
                    "type": "groupby",
                    "params": {
                        "function_id": "aggregate",
                        "group_by": ["Department"],
                        "values": [
                            {
                                "function_id": "count_distinct",
                                "expression": "Project_ID"
                            }
                        ]
                    }
                },
                {
                    "type": "groupby",
                    "params": {
                        "function_id": "aggregate",
                        "group_by": ["Department"],
                        "values": [
                            {
                                "function_id": "sum",
                                "expression": "case_when(status)"
                            }
                        ]
                    }
                },
                {
                    "type": "case_when",
                    "params": {
                        "function_id": "case_when",
                        "condition_type": "SINGLE_COLUMN",
                        "source_column": "status",
                        "conditions": [
                            {
                                "operator": "=",
                                "condition": "Completed",
                                "value": 1
                            },
                            {
                                "operator": "!=",
                                "condition": "Completed",
                                "value": 0
                            }
                        ],
                        "target_column": "completed_projects"
                    }
                },
                {
                    "type": "groupby",
                    "params": {
                        "function_id": "aggregate",
                        "group_by": ["Department"],
                        "values": [
                            {
                                "function_id": "sum",
                                "expression": "case_when(status)"
                            }
                        ]
                    }
                },
                {
                    "type": "case_when",
                    "params": {
                        "function_id": "case_when",
                        "condition_type": "SINGLE_COLUMN",
                        "source_column": "status",
                        "conditions": [
                            {
                                "operator": "=",
                                "condition": "In progress",
                                "value": 1
                            },
                            {
                                "operator": "!=",
                                "condition": "In progress",
                                "value": 0
                            }
                        ],
                        "target_column": "in_progress_projects"
                    }
                },
                {
                    "type": "rename",
                    "params": {
                        "function_id": "biz_rename",
                        "rename_type": "special_name",
                        "conditions": [
                            {
                                "source_column": "Project_ID",
                                "target_column": "total_projects"
                            }
                        ]
                    }
                },
                {
                    "type": "select",
                    "params": {
                        "function_id": "keep_columns",
                        "column_type": "multiple",
                        "source_columns": [
                            "Department",
                            "total_projects",
                            "completed_projects",
                            "in_progress_projects"
                        ]
                    }
                }
            ]
        }
    }
}

create_and_populate_db('knowledge_base.db', knowledge_base)
