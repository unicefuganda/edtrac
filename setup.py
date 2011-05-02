from setuptools import setup

setup(
    name='rapidsms-generic',
    version='0.1',
    license="BSD",

    install_requires = [
		"rapidsms",
		
	],

    description='An extension for associating contacts with django users and groups.',
    long_description=open('README.rst').read(),
    author='David McCann',
    author_email='david.a.mccann@gmail.com',

    url='http://github.com/daveycrockett/rapidsms-generic',
    download_url='http://github.com/daveycrockett/rapidsms-generic/downloads',

    include_package_data=True,

    packages=['generic'],
    package_data={'generic':['templates/*/*.html','templates/*/*/*.html','static/*','static/*/*']},
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
