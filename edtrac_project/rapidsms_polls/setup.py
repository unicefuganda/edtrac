from setuptools import setup, find_packages

setup(
    name='rapidsms-polls',
    version='0.1',
    license="BSD",

    install_requires = ["rapidsms", 'django-uni-form', 'django-eav'],

    dependency_links = [
        "http://github.com/mvpdev/django-eav/tarball/master#egg=django-eav",
    ],

    description='An application for a simple communication modality with SMS users: prompted questions, simple, training-less answers.',
    long_description=open('README.rst').read(),
    author='David McCann',
    author_email='david.a.mccann@gmail.com',

    url='http://github.com/daveycrockett/rapidsms-polls',
    download_url='http://github.com/daveycrockett/rapidsms-polls/downloads',

    include_package_data=True,

    packages=find_packages(),
    package_data={'poll':[
        'templates/*/*.html',
        'templates/*/*/*.html',
        'static/images/*',
        'static/javascripts/*',
        'static/stylesheets/*',
        'static/icons/silk/*']},
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
