"""
temporarily for testing
"""
from svisitor import SVisitor
import os

if __name__ == '__main__':
    sv = SVisitor()
    os.chdir('../example')
    sv.single_file_1st_pass('_code_example2.py')
    sv.sgraph.visualize('../_', view=True)
