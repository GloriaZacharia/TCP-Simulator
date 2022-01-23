from socket import socket
from sys import argv
from time import sleep
import random
import json


class State: 
    CurrentContext = None
    def __init__(self, Context):
        self.CurrentContext = Context
    def trigger(self):
        return True

class StateContext:
    state = None
    CurrentState = None
    availableStates = {}

    def setState(self, newstate):
        try:
            self.CurrentState = self.availableStates[newstate]
            self.state = newstate
            self.CurrentState.trigger()
            return True
        except KeyError: #incorrect state key specified
            return False

    def getStateIndex(self):
        return self.state

class Transition:
    def passive_open(self):
        print("Error!")
        return False
    def syn(self):
        print("Error!")
        return False
    def ack(self):
        print("Error!")
        return False
    def rst(self):
        print("Error!")
        return False
    def syn_ack(self):
        print("Error!")
        return False
    def close(self):
        print("Error!")
        return False
    def fin(self):
        print("Error!")
        return False
    def timeout(self):
        print("Error!")
        return False
    def active_open(self):
        print("Error!")
        return False

class Closed(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def passive_open(self):
        self.CurrentContext.listen()
        print("Transitioning to LISTEN state.....")
        self.CurrentContext.setState("LISTEN")
        return True
    def rst(self):
        print("Reseting connection...")
        self.CurrentContext.setState("CLOSED")
        return True
    def trigger(self):
        try:
            print("Closing connection...")
            self.CurrentContext.connection.close() #attempt to terminate socket
            return True
        except: #no current connection
            return False

class Listen(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def syn(self):
        command=self.CurrentContext.connection.recv(1024)
        print("Received SYN packet")
        msg=command.decode()
        a=json.loads(msg)
        self.CurrentContext.acknowledgementNo=a["SequenceNo"]+1
        print("Transitioning to SYNRECVD state...")
        self.CurrentContext.setState("SYNRECVD")
        return True
    def trigger(self):
        return self.CurrentContext.syn()

class SynRecvd(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def ack(self):
        command=self.CurrentContext.connection.recv(1024)
        msg=command.decode()
        a=json.loads(msg)
        b=a["acknowledgementNo"]
        if b ==self.CurrentContext.SequenceNo+1:
            print("Received ACK packet...")
            print("Transitioning to ESTABLISHED state...")
            self.CurrentContext.setState("ESTABLISHED")
        return True
    def trigger(self):
        print("Sending SYN_ACK packet...") 
        data={"SequenceNo":self.CurrentContext.SequenceNo, "acknowlegementNo":self.CurrentContext.acknowledgementNo}
        tosend=json.dumps(data)
        self.CurrentContext.connection.send(tosend.encode())
        return self.CurrentContext.ack()

class Established(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def fin(self):
        print("Transitioning to CLOSE_WAIT state...")
        self.CurrentContext.setState("CLOSE_WAIT")
        return True
    def trigger(self):
        def ss_encrypt_decrypt(inputtext, secretkey, encrypt):
            endkeyposition=len(secretkey)-1
            currentkeyposition = 0
            outputtext = ""
            #Encrypt/decrypt file using secret key
            for inputtextbyte in inputtext:
                if currentkeyposition > endkeyposition: currentkeyposition %= endkeyposition
                #XOR used to encrypt
                outputbyte=ord(inputtextbyte) ^ ord(secretkey[currentkeyposition])
                outputtext += chr(outputbyte)
                #Move one position to the right on encryption key
                if encrypt:
                    currentkeyposition+=outputbyte
                else:
                    currentkeyposition+= ord (inputtextbyte)
            return outputtext
        while True:
            encryptedtext=self.CurrentContext.connection.recv(1024) #1024 bytes
            msg=encryptedtext.decode()
            try:#look for non-data packet (e.g. tcp fin)
                a=json.loads(msg)
                b=a["SequenceNo"]
                self.CurrentContext.acknowledgementNo=b+1
                print("Received FIN packet and attempting to close connection!!")
                break
            except:
                encryptedtext = encryptedtext.decode()
                print("Received: "+encryptedtext)
                cleartext=ss_encrypt_decrypt(encryptedtext, "UniversityOfSouthWales", False)
                cleartext = cleartext.upper()
                encryptedtext=ss_encrypt_decrypt(cleartext, "UniversityOfSouthWales", True)
                print("Sending: " + encryptedtext)
                self.CurrentContext.connection.send(encryptedtext.encode())
        return self.CurrentContext.fin()

class CloseWait(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def close(self):
        print("Transitioning to LAST_ACK state....")
        self.CurrentContext.setState("LAST_ACK")
        return True
    def trigger(self):
        print("Sending an ACK packet...")
        data={"SequenceNo":self.CurrentContext.SequenceNo,"acknowledgementNo":self.CurrentContext.acknowledgementNo}
        toSend=json.dumps(data)
        self.CurrentContext.connection.send(toSend.encode())
        return self.CurrentContext.close()

class LastAck(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def ack(self):
        command=self.CurrentContext.connection.recv(1024)
        msg=command.decode()
        a=json.loads(msg)
        c=a["acknowledgementNo"]
        if c==self.CurrentContext.SequenceNo+1:
            print("Received ACK packet...")
            print("Transitioning to CLOSED state...")
            self.CurrentContext.setState("CLOSED")
        return True
    def trigger(self):
        print("Sending FIN packet...")
        data={"SequenceNo":self.CurrentContext.SequenceNo,"acknowledgementNo":self.CurrentContext.acknowledgementNo}
        toSend=json.dumps(data)
        self.CurrentContext.connection.send(toSend.encode())
        return self.CurrentContext.ack()

class TCPServer(StateContext,Transition):
    def __init__(self):
        self.sleep_time = 0
        self.host = "127.0.0.1"
        self.port = 5001
        self.connection_address = 0
        self.socket = None
        self.SequenceNo=random.randint(0,2000)
        self.acknowledgementNo=0
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["LISTEN"] = Listen(self)
        self.availableStates["SYNRECVD"] = SynRecvd(self)
        self.availableStates["ESTABLISHED"] = Established(self)
        self.availableStates["CLOSE_WAIT"] = CloseWait(self)
        self.availableStates["LAST_ACK"] = LastAck(self)
        print("Transitioning to closed!")
        self.setState("CLOSED")
        

    def passive_open(self):
        return self.CurrentState.passive_open()
    def syn(self):
        return self.CurrentState.syn()
    def ack(self):
        return self.CurrentState.ack()
    def rst(self):
        return self.CurrentState.rst()
    def close(self):
        return self.CurrentState.close()
    def fin(self):
        return self.CurrentState.fin()
    
    def listen(self):
        '''this method initiates a listen socket'''
        try:
            self.socket = socket()
            self.socket.bind((self.host,self.port))
            self.socket.listen(1)
            self.connection, self.connection_address = self.socket.accept() #connection acceptance
        except Exception as err:
            print(err)
            exit()

if __name__=='__main__':
    Activepeer=TCPServer()
    Activepeer.passive_open()
    
       

        



    

      
