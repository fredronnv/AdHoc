# RPCC (RPC at Chalmers)
Chalmers Multiprotocol RPC server framework

RPCC is a framework that makes possible to quickly develop RPC servers
in Pyrthon. The servers may be run on any supported python platforms,
including Linux, Mac OS or Windows.

The RPC functions may be called using SOAP or JSON, and built into the
framework is the generation of documentation given the definitions made
the source code of the developed server.

On a conceptual level, RPCC may be compared to WCF under .NET even if 
a server written using RPCC can also be run n Windows.

History:
RPCC started as "The RPC Server" -framework used to write
Chalmers Person Database server in 2007. Then framework could by then only 
interpret XMLRPC. One year later SOAP support was added to the framework, 
including automatic WSDL generation, which only increased the code base with about 15%. 
THE Person database thus got SOAP support without any extra labor for the server developers.

In 2009 support for parallel API versions was added to support
changes in existing types and functions that do not break the
existing clients.

In 2012 an afternoon was devoted to add JSON support, and since then
JSON is the recommended access method for clients that do not need – or want – to
take on the full load of using SOAP.

Development of "rpc server" to become RPC
Over the years, much functionality was developed for the Person database server that in fact
is useful for RPC servers in general. Lots of such code has been ported to RPCC as optional
functions. In addition, many necessary improvements have been
made:

* Simplified database access. Thread-safe pooling of links to databases that need it (Oracle still takes 0.1 seconds to create a new link). Translation of parameter formas.

* Return type checking. A function cannot not return a type that differs from its documentation.
* Mutexes and mutex variables. Most clients to RPC servers may want to to keep track of simple data between runs, and make sure that parallel instances do not run simultaneously.
* Support for monitoring clients by watchdogs.
* An event system, where you can register changes in a searchable change log.
* A standardized data model (PDB's Object / Object Handler). Simplifies coding of the server considerably.
* Data formatters, using the standardized data model can create return data with client-specified fields, following links between data types. 
* Data searchers, which provides searchability both in SQL and in generated attributes, and that can follow links between data types. 
* Dig-functions, based on the above two, that provides advanced searching possibilites and allows for the filtering of the returned data.
* Ability to easily create access controls and mark up the methods of the data model with eligibility requirements.
* Semi-automatic database tables generation based on the specified data model.
* Support for MySQL, PostGreSQL and even SQLite over and above the original Qracle Support.
