from setuptools import setup

setup(
    name='rapidsms-contact',
    version='0.1',
    license="BSD",

    install_requires = ["rapidsms", 'rapidsms-generic'],

    dependency_links = [
        "http://github.com/daveycrockett/rapidsms-generic/tarball/master#egg=rapidsms-generic"
    ],

    description='Views for generic contact management.',
    long_description=open('README.rst').read(),
    author='Mugisha Moses',
    author_email='mossplix@gmail.com',

    url='http://github.com:/mossplix/rapidsms-contact',
    download_url='http://github.com:/mossplix/rapidsms-contact/downloads',

    include_package_data=True,

    packages=['contact'],
    package_data={packages[0]:['templates/*/*.html','templates/*/*/*.html']},
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
