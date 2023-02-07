# gNMI Device Test Cases

## Sanity tests


### Capabilities

The case verifies that the device correctly responds to the `Capabilities` RPC.

* **Parameters**

  Connection parameters (address and port, credentials, connection type, certificates)

* **Failure**

  Device fails to respond, responds with empty supported model set, responds
  with supported encodings set that does not contain `JSON_IETF`.
  
* **Warning**

  Device responds with supported encodings set that does not contain `JSON`.


### Get

The case verifies basic functionality of the `Get` RPC.

* **Parameters**

  Connection parameters, path.
  
* **Failure**

  Device does not respond, responds with an error, responds with an empty
  notification set or with a notification without updates, responds with
  incorrect encoding.
  
  
## Detailed tests

### Get target

The case verifies correct behavior of the `target` field.

* **Parameters**

  Connection parameters, path.
  
* **Failure**

  Device' response does not correctly reflect `target` field in the request.
 
 
## Performance tests

### Parallel subscribe

The case verifies that the device is capable of handling several parallel
subscriptions.  The test creates several (5-10) streaming subscriptions and
verifies that the device is able to supply updates to all of them.

* **Parameters**

  Connection parameters, path.
  
* **Failure**

  Device fails to provide updates to any of the subscriptions.
  

