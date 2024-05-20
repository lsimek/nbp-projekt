"""
temporarily for testing
"""
from svisitor import SVisitor

sv = SVisitor()
sv.single_file('../example/code_example.py')
sv.sgraph.visualize('../_', view=True)
