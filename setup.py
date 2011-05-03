from setuptools import setup

setup(
    name='rapidsms-unregister',
    version='0.1',
    license="BSD",

    # install_requires = ["rapidsms",
    #                 'django-eav',
    #                 'rapidsms-auth',
    #                 'rapidsms-polls',
    #                 'simple_locations'
    #     ],
    # 
    #     dependency_links = [
    #         "http://github.com/mvpdev/django-eav/tarball/master#egg=django-eav",
    #         "http://github.com/daveycrockett/auth/tarball/master#egg=rapidsms-auth",
    #         "http://github.com/daveycrockett/rapidsms-polls/tarball/master#egg=rapidsms-polls",
    #         "http://github.com/mossplix/simple_location/tarball/master#egg=simple_locations",
    #     ],

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
