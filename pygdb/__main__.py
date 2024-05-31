"""
temporarily for testing
"""
from svisitor import SVisitor
import os
from pathlib import Path

if __name__ == '__main__':
    # # analyse this project
    # startpath = Path(os.getcwd())
    # sv = SVisitor(root_namespace='pygdb')
    # os.chdir(startpath / Path('.'))
    # sv.scan_package(root_dir=os.getcwd())
    # sv.sgraph.visualize(startpath / Path('../_'), 'png', view=True)

    os.chdir('/home/lsimek/projects/nbp-projekt')
    startpath = Path(os.getcwd())
    sv = SVisitor(root_namespace='test_package')
    os.chdir(startpath / Path('test/test_package/'))
    sv.scan_package(root_dir=os.getcwd())
    sv.sgraph.visualize(startpath / Path('_'), 'png', view=True)

    # startpath = Path(os.getcwd())
    # sv = SVisitor(root_namespace='numpy')
    # os.chdir(startpath / Path('../_numpy/numpy/'))
    # sv.scan_package(root_dir=os.getcwd())
    # #sv.sgraph.visualize(startpath / Path('../_'), 'png', view=True)

