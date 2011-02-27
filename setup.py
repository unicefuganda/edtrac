from distutils.core import setup

setup(
    name='auth',
    version='0.1',
    license="BSD",

    requires = ["rapidsms", 'python (>= 2.5)', 'django (>= 1.2)'],

    description='An extension for associating contacts with django users and groups.',
    long_description=open('README.rst').read(),
    author='David McCann',
    author_email='david.a.mccann@gmail.com',

    url='http://github.com/daveycrockett/auth',
    download_url='http://github.com/daveycrockett/auth/downloads',

    include_package_data=True,

    packages=['auth'],

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
