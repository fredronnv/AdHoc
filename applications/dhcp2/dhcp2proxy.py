#!/usr/bin/env python
'''
Created on 28 jan 2014

@author: bernerus
'''
import sys
import kerberos
import pprint

true=True
false=False

def template2keys(template, indent=1):
    #print >>sys.stderr, "    " * indent + "Template2keys: template=", template, "indent=", indent
    kvtuples = []
    ltemplate = template
    for k in ltemplate.split(","):
        if k:
            k = k.strip()
        if k.startswith('{'): 
            k = k[1:]
        if k.endswith('}'):
            k = k[:-1]
        #print >>sys.stderr, "    " * indent + "splitting:", k
        try:
            (key, val) = k.split(":", 1)
        except ValueError:
            print >>sys.stderr, "Invalid value:", k
            raise
        if key.startswith('"') or key.startswith("'"):
            key = key[1:]
        if key.endswith('"') or key.endswith("'"):
            key = key[:-1]
        kvtuples.append((key, val))
    #print >>sys.stderr, "    " * indent + "Template2keys: kvtuples=", kvtuples
    return kvtuples


def print_struct_in_order(x, kvtuples, template, output, indent=1):
    #print >>sys.stderr, "    " * indent + "print_struct_in_order: x=", x, "kvtuples=", kvtuples, "template=", template, "indent=", indent
    values = []
    for kvtuple in kvtuples:
        key = kvtuple[0]
        if key.startswith('_'):
            continue
        keyval = kvtuple[1].strip()
        if keyval == "False" or keyval == "false":  # Hmm, this is probably not supported
            raise ValueError("Never use False as a value to _dig or _fetch functions")
        if keyval == "True" or keyval == "true":
            if x[key]:
                if type(x[key]) is list:
                    values.append(x[key])
                else:
                    values.append(unicode(x[key]))
            else:
                values.append("NULL")
        else:
            print_object_in_template_order(x[key], keyval, output, indent=indent + 1)
            output.write(" \t")
    #print >>sys.stderr, "VALUES=", values
    if len(values) == 1 and type(values[0]) is list:
        #print >>sys.stderr ,"LIST=", values[0]
        output.write("\n".join(values[0]))
    else:  
        output.write(" \t".join(values))
    
    
def print_object_in_template_order(obj, template, output, indent=1):
    #print >>sys.stderr, "    " * (indent - 1) + "  " + "print_object_in_template_order: obj=", obj, "template=", template, "indent=", indent
    if type(obj) is list:
        for o in obj:
            print_object_in_template_order(o, template, output, indent + 1)
            print >>output
    else:
        kvtuples = template2keys(template, indent)
        print_struct_in_order(obj, kvtuples, template, output, indent=indent)
 
 
def process(command, output):
    global srv, srv_url
    
    res = None
    (cmd, sep, arg) = command.partition("(")
    #print >>sys.stderr, "CMD=",cmd, "sep=", sep, "arg=",arg
    arg = arg.strip()
    if sep:
        arg = arg.rstrip(")")
    #print >>sys.stderr, "CMD=",cmd, "sep=", sep, "arg=",arg
    
    try:
        if not srv:
            if not srv_url:
                srv_url = "https://adhoc.ita.chalmers.se:8877"
            srv = rpcc_client.RPCC(srv_url)
        
        s = cmd + "(" + arg + ")"
        
        #print >> sys.stderr, "CMD=%s" % cmd
        #print >> sys.stderr, "EXEC: %s" % s
        try:
            exec s
            #print >>sys.stderr, "EXEC DONE"
        except rpcc_client.RPCCRuntimeError, e:
            e=e[0]
            try:
                if e.name == 'RuntimeError::AccessDenied':
                    print >>sys.stderr, "Access denied. Needed privileges %s" % e.desc.lower()
                else:
                    print >>sys.stderr, "%s: %s" % (e.name, e.desc)
            except:
                print >>sys.stderr, "Unexpected error from server:", e
            raise
            
        except (rpcc_client.RPCCValueError,rpcc_client.RPCCLookupError,rpcc_client.RPCCTypeError),  e:
            e=e[0]
            try:
                if e["value"]:
                    print >>sys.stderr, "%s: %s" % (e.desc, e.value)
                else:
                    print >>sys.stderr, "%s" % e.desc
            except:
                print >>sys.stderr, "Unexpected error from server:", e
            raise
        
        except kerberos.GSSError:
            raise
             
        except Exception, e:
            print >>sys.stderr, "Exception on command:", e
            raise
        #print >> sys.stderr, "RES=%s" % res
        s = ""
        if cmd.endswith("_dig") or cmd.endswith("_fetch"):
        # Extract the last argument as the template
            depth=0 
            template=""
            for i in range(len(arg)-1,0,-1):
                if arg[i]=='}':
                    depth += 1
                    continue
                if arg[i]=='{':
                    depth -= 1
                    continue
                if arg[i] == ',' and depth==0:
                    template=arg[i+1:]
                    break
            else:
                print >>sys.stderr, "Syntax error to dig or fetch RPC. Cannot find data template parameter"
            	return 1

            print_object_in_template_order(res, template, output)
            return 0
                
        if type(res) is unicode or type(res) is str:
            s = res
            
        if type(res) is not None:  
            output.write(s)
            
        #print output.getvalue().rstrip('\n')
        #print >>sys.stderr, "OBJECT VALUE='" + output.getvalue()+"'"
        return 0
    
    except kerberos.GSSError:
            print >> sys.stderr
            print >> sys.stderr, "You need a Kerberos ticket. See kinit(1)"
            print >> sys.stderr
            raise
                
    except KeyError, e:
        print >> sys.stderr, e
        try:
            print >> sys.stderr, "ERROR: %s: %s" % (e[0].desc, e[0].value)
        except:
            print >> sys.stderr, "ERROR:", e
        return 1
    
    
import os
import StringIO
srv_url = None
srv = None
import rpcc_client

fifo_in = sys.argv[1]
fifo_out = sys.argv[2]

update_template = {}  # For use by dhcp2
options = {}  # For use by dhcp2

while True:
        fin = open(fifo_in, "r")
        fout = open(fifo_out, "w")
        sys.stdout = fout
        #print >>sys.stderr, fin
        finval = fin.read()
        #print >>sys.stderr, "Finval=", finval
        output = StringIO.StringIO()
        try:
            process(finval, output) 
            outres = output.getvalue().rstrip("\n").encode("utf-8")
            print outres
            sys.stdout.flush()
        except:
            sys.stdout.flush()
            sys.stderr.flush()
            fout.close()
            fin.close()
            sys.exit(1)
        fout.close()
        fin.close()
