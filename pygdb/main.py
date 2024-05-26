"""
temporarily for testing
"""
from svisitor import SVisitor
import os

if __name__ == '__main__':
    sv = SVisitor(root_namespace='test')
    os.chdir('../test')
    sv.single_file_first_pass('test_module.py')
    sv.sgraph.visualize('../_', view=True)
