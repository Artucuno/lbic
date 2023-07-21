# Create setup.py
from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='lbic',
    version='0.0.1',
    packages=['lbic', 'lbic.utils'],
    package_dir={'': 'src'},
    url='https://github.com/Artucuno/lbic',
    license='MIT',
    author='Artucuno',
    description='A load balanced interactions.py client',
    python_requires='>=3.8',
    install_requires=required,

)