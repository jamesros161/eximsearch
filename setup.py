import setuptools

setuptools.setup(

     name='exmsearch',  

     version='0.9',

     scripts=['bin/exmsearch'] ,

     author="James Rosado",

     author_email="dev@twmsllc.com",

     description= ("Exim Search Utility "),

     url="https://github.com/twmsllc/eximsearch",

     packages=setuptools.find_packages(),

     classifiers=[

         "Programming Language :: Python :: 3.6",

         "License :: GNU General Public License",

     ],

 )
