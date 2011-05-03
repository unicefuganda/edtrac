from setuptools import setup

setup(
    name='uganda_common',
    version='0.1',
    license="BSD",

    install_requires = ["rapidsms"],

    description='A suite of utility functions for Uganda RSMS deployments.',
    long_description='',
    author='UNICEF Uganda T4D',
    author_email='mossplix@gmail.com',

    url='http://github.com/mossplix/uganda_common',
    download_url='http://github.com/mossplix/uganda_common/downloads',

    include_package_data=True,

    packages=['uganda_common'],

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
