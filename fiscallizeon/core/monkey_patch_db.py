# FUNÇÃO PARA DEBUGAR AS QUERIES
# import logging
# from django.db.backends.utils import CursorWrapper

# logger = logging.getLogger("db_query_logger")

# def patch_cursor():
#     original_execute = CursorWrapper.execute
#     original_executemany = CursorWrapper.executemany

#     def execute(self, sql, params=None):
#         db_alias = getattr(self.db, 'alias', 'unknown')
        
#         if db_alias == 'default' and sql.startswith('SELECT'):
#             print("-" * 50)
#             print("🚀 ~ alias:", db_alias) 
#             print("🚀 ~ query:", sql) 
#             print("🚀 ~ params:", params) 
#             print("-" * 50)
            
#         logger.debug(f"[{db_alias}] {sql}")
#         return original_execute(self, sql, params)

#     def executemany(self, sql, param_list):
#         db_alias = getattr(self.db, 'alias', 'unknown')
        
#         if db_alias == 'default' and sql.startswith('SELECT'):
#             print("-" * 50)
#             print("🚀 ~ alias:", db_alias) 
#             print("🚀 ~ query:", sql) 
#             print("🚀 ~ params:", param_list)  
#             print("-" * 50)
            
#         logger.debug(f"[{db_alias}] {sql}")
#         return original_executemany(self, sql, param_list)

#     CursorWrapper.execute = execute
#     CursorWrapper.executemany = executemany