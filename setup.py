from setuptools import setup, find_packages

setup(
    name='droneblocks-python-utils',
    version='0.1',
    packages=find_packages(include=['droneblocks', 'droneblocks.*', 'droneblocksutils', 'droneblocksutils.*']),
    package_data={
        'droneblocks': ['data/placeholder.txt']
    },
    url='https://github.com/dbaldwin/DroneBlocks-Python-Utils',
    license='',
    author='patrick ryan',
    author_email='theyoungsoul@gmail.com',
    description='DroneBlocks Python Utilities',
    install_requires=[
        'opencv-python==4.5.3.56',
        'opencv-contrib-python==4.5.3.56',
        'imutils==0.5.4',
        'djitellopy2==2.3',
    ]
)
