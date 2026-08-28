import os
import ast
from pathlib import Path
ENVIRONMENT_FILE_AND_FOLDER = ['__pycache__', '.venv', '.env', '.git', 'venv', 'env', '.idea', '.vscode', 'node_modules', 'project_documentation.md', 'project_diagram.py']
class FunctionDiagram:
    def __init__(self):
        self.function = None
        self.name_function = None
        self.doc_function = None
        self.decorator = []
        self.function_read_only = False

    def _get_decorator_name(self, function_decorator):
        if isinstance(function_decorator, ast.Name):
            return function_decorator.id
        elif isinstance(function_decorator, ast.Attribute):
            return f'{self._get_decorator_name(function_decorator.value)}.{function_decorator.attr}'

    def add_function(self, function: ast.FunctionDef):
        '''
        function: hàm cần được ghi vào;
        note: ghi chú về hàm
        '''
        self.function = function
        self.name_function = function.name
        self.doc_function = ast.get_docstring(function)
        for function_decorator in function.decorator_list:
            decorator_name = self._get_decorator_name(function_decorator)
            if decorator_name:
                self.decorator.append(decorator_name)

    def lock_function(self):
        self.function_read_only = True

    def write_doc(self):
        doc = f'''#### Tên hàm: {self.name_function} \n
                Decorator: {self.decorator} \n
                Mô tả hàm: {self.doc_function} \n
                Chỉ đọc: {self.function_read_only} \n'''
        return doc
    
class ClassDiagram:
    def __init__(self):
        self.class_data = None
        self.name_class = None
        self.doc_class = None
        self.list_function = []
        self.inheritor = []
        self.class_read_only = False

    def _get_node_name(self, obj):
        if isinstance(obj, ast.Name):
            return obj.id
        if isinstance(obj, ast.Attribute):
            return f'{self._get_node_name(obj.value)}.{obj.attr}'

    def add_class(self, class_data):
        '''
        class_data: class cần được ghi vào;
        note: ghi chú về class
        '''
        self.class_data = class_data
        self.name_class = class_data.name
        self.doc_class = ast.get_docstring(class_data)

        for function in class_data.body:
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_diagram = FunctionDiagram()
                function_diagram.add_function(function=function)
                self.list_function.append(function_diagram)
        self.class_inheritor()

    def class_inheritor(self):
        for class_inheritor in self.class_data.bases:
            name = self._get_node_name(class_inheritor)
            if name:
                self.inheritor.append(name)

    def lock_class(self):
        self.class_read_only = True

    def write_doc(self):
        list_name_function = []
        for name in self.list_function:
            list_name_function.append(name.name_function)

        doc = f'''### Tên Lớp: {self.name_class} \n
            Mô tả lớp: {self.doc_class} \n
            Các lớp được lớp này thừa kế: {self.inheritor} \n
            Các hàm trong lớp này: {list_name_function} \n
            Chỉ đọc: {self.class_read_only} \n'''
        for function in self.list_function:
            doc_function = function.write_doc()
            doc += doc_function

        return doc
    
class FileDiagram:
    def __init__(self):
        self.file_name = None
        self.list_class = []
        self.list_function = []
        self.doc_file = None
        self.file_read_only = False

    def add_file(self, tree, file):
        '''
        tree: Cây hệ thống của python;
        file: tên file cần nhập
        '''
        
        self.file_name = file
        self.doc_file = ast.get_docstring(tree)
        for obj in tree.body:
            if isinstance(obj, ast.ClassDef):
                class_diagram = ClassDiagram()
                class_diagram.add_class(obj)
                self.list_class.append(class_diagram)

        for obj in tree.body:
            if isinstance(obj, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_diagram = FunctionDiagram()
                function_diagram.add_function(obj)
                self.list_function.append(function_diagram)

    def lock_file(self):
        self.file_read_only = True

    def write_doc(self):
        list_class_name = []
        for class_name in self.list_class:
            list_class_name.append(class_name.name_class)

        list_function_name = []
        for function_name in self.list_function:
            list_function_name.append(function_name.name_function)

        doc = f'''## Tên file: {self.file_name} \n
            Mô tả file: {self.doc_file} \n
            Các class trong file: {list_class_name} \n
            Các hàm lẻ trong file: {list_function_name} \n
            Chỉ đọc: {self.file_read_only} \n'''
        for class_data in self.list_class:
            doc += class_data.write_doc()
        
        for function in self.list_function:
            doc += function.write_doc()

        return doc

class ProjectDiagram:

    def __init__(self):
        self.name_project = None
        self.list_file = []
        self.doc_project = None
        self.project_read_only = False

    def _reset_project(self):
        self.name_project = None
        self.list_file = []
        self.doc_project = None
        self.project_read_only = False

    def add_project(self, folder_project):
        '''
        folder_project: Thư mục chứa dự án'''
        self._reset_project()
        self.name_project = os.path.basename(folder_project)
        for readme in os.listdir(folder_project):
            if readme.lower() == 'readme.md':
                readme_path = os.path.join(folder_project, readme)
                with open(readme_path, 'r', encoding='utf-8') as file:
                    self.doc_project = file.read()
                break

        for root, dirs, files in os.walk(folder_project):
            dirs[:] = [
                directory for directory in dirs
                if directory not in ENVIRONMENT_FILE_AND_FOLDER
            ]
            for file in files:
                if (
                    file.endswith('.py')
                    and file not in ENVIRONMENT_FILE_AND_FOLDER
                ):
                    try:
                        file_path = os.path.join(root, file)
                        file_name = Path(file_path).parts
                        idx = file_name.index(self.name_project)
                        result_file_name = Path(*file_name[idx:]).as_posix()

                        with open(file_path, 'r', encoding='utf-8') as source_file:
                            source = source_file.read()

                        tree = ast.parse(source=source, filename=file_path)

                        file_diagram = FileDiagram()
                        file_diagram.add_file(tree, result_file_name)
                        self.list_file.append(file_diagram)
                    except Exception as e:
                        print(f"Syntax error in {file_path}: {e}")
    def lock_project(self):
        self.project_read_only = True

    def write_doc(self):
        list_file_name = []
        for file_name in self.list_file:
            list_file_name.append(file_name.file_name)

        doc = f'''# Tên dự án: {self.name_project} \n
            Mô tả dự án: {self.doc_project} \n
            Các file trong dự án: {list_file_name} \n
            Chỉ đọc: {self.project_read_only} \n'''
        for file_data in self.list_file:
            doc += file_data.write_doc()

        return doc

class ToanHoc:
    def cong(self, a, b): return a + b
    def tru(self, a, b): return a - b

    @staticmethod
    def nhan(a, b): return a*b

if __name__ == '__main__':
    p = ProjectDiagram()
    p.add_project(r'D:\rag_project')
    with open('project_documentation.md', 'w', encoding='utf-8') as file:
        file.write(p.write_doc())
