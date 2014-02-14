from setuptools import setup

setup(
    name='rapidsms-unregister',
    version='0.1',
    license="BSD",

    install_requires = [
        "rapidsms",
    ],

    description='An application for blacklisting numbers that want to opt-out of this application, disabling all further SMS interactions with the user.',
    long_description=open('README.rst').read(),
    author='David McCann',
    author_email='david.a.mccann@gmail.com',

    url='http://github.com/daveycrockett/rapidsms-unregister',
    download_url='http://github.com/daveycrockett/rapidsms-unregister/downloads',

    include_package_data=True,

    packages=['unregister'],
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
