"""
temporarily for testing
"""
from svisitor import SVisitor
import os
from pathlib import Path

if __name__ == '__main__':
    startpath = Path(os.getcwd())
    sv = SVisitor(root_namespace='test_package')
    os.chdir(startpath / Path('../test/test_package/'))
    sv.scan_package(root_dir=os.getcwd())
    sv.sgraph.visualize(startpath / Path('../_'), 'png', view=True)
