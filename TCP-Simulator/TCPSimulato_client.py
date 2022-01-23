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

class Closed(State, Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def rst(self):
        print("Transitioning to CLOSED state...")
        self.CurrentContext.setState("CLOSED")
        return True
    def active_open(self):
        self.CurrentContext.make_connection()
        print("Transitioning to SYN_SENT state...")
        self.CurrentContext.setState("SYN_SENT")
        return True
    def trigger(self):
        try:
            self.CurrentContext.socket.close() #attempt to terminate socket
            print("Closing connection!")
            return True
        except: #no current connection
            return False

class SynSent(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def rst(self):
        print("Transitioning to CLOSED state...")
        self.CurrentContext.setState("CLOSED")
        return True
    def timeout(self):
        print("Transitioning to CLOSED state...")
        self.CurrentContext.setState("CLOSED")
        return True
    def syn_ack(self):
        print("Transitioning to ESTABLISHED state...")
        self.CurrentContext.setState("ESTABLISHED")
        return True
    def trigger(self):
        print("Sending SYN packet...")
        data = {"SequenceNo":self.CurrentContext.SequenceNo}
        tosend=json.dumps(data)
        self.CurrentContext.socket.send(tosend.encode())
        try:
            command = self.CurrentContext.socket.recv(1024)
            msg=command.decode()
            a=json.loads(msg)
            c=a["SequenceNo"]
            b=a["acknowlegementNo"]
            if b==self.CurrentContext.SequenceNo +1:
                self.CurrentContext.SequenceNo=b
                self.CurrentContext.acknowledgementNo=c+1
                print("Received SYN_ACK packet...")
                return self.CurrentContext.syn_ack()
        except:
            print ("Data not received [timeout]!")
            return self.CurrentContext.timeout()
class Established(State, Transition):
    def __init__(self, Context):
        State.__init__(self,Context)
    def close(self):
        print("Transitioning to FINWAIT1 state...")
        self.CurrentContext.setState("FINWAIT1")
        return True
    def trigger(self):
        print("Sending ACK packet...")
        data={"SequenceNo" : self.CurrentContext.SequenceNo,"acknowledgementNo": self.CurrentContext.acknowledgementNo}
        toSend=json.dumps(data)
        self.CurrentContext.socket.send(toSend.encode())
        print("Established!!")
        def ss_encrypt_decrypt(inputtext, secretkey, encrypt):
            endkeyposition=len(secretkey)-1
            currentkeyposition = 0
            outputtext = ""
            for inputtextbyte in inputtext:
                if currentkeyposition > endkeyposition:currentkeyposition%=endkeyposition
                #XOR used to encrypt
                outputbyte=ord(inputtextbyte) ^ ord(secretkey[currentkeyposition])
                outputtext+=chr(outputbyte)
                #Move one position to the right on encryption key
                if encrypt:
                    currentkeyposition+=outputbyte
                else:
                    currentkeyposition+=ord(inputtextbyte)
            return outputtext
        print()
        print("If you want to quit enter Q ")
        cleartext=input("Message: ")
        while cleartext !="Q":
            encryptedtext = ss_encrypt_decrypt(cleartext, "UniversityOfSouthWales", True)
            print ("Sending: " + encryptedtext)
            self.CurrentContext.socket.send(encryptedtext.encode())
            encryptedtext=self.CurrentContext.socket.recv(1024)
            encryptedtext=encryptedtext.decode()
            print("Received: " + encryptedtext )
            cleartext = ss_encrypt_decrypt(encryptedtext, "UniversityOfSouthWales", False)
            print("Decrypted: "+cleartext)
            print()
            cleartext=input("Message: ")
        return self.CurrentContext.close()
    
class FinWait_1(State, Transition):
    def __init__(self, Context):
        State.__init__(self,Context)
    def ack(self):
        command = self.CurrentContext.socket.recv(1024)
        msg=command.decode()
        a=json.loads(msg)
        b=a["SequenceNo"]
        c=a["acknowledgementNo"]
        if c==self.CurrentContext.SequenceNo+1:
            print("Received ACK packet...")
            self.CurrentContext.SequenceNo=c
            self.CurrentContext.acknowledgementNo=b+1
            print("Transitioning to FINWAIT2 state...")
            self.CurrentContext.setState("FINWAIT2")
        return True
    def trigger(self):
        print("Sending FIN packet...")
        data={"SequenceNo":self.CurrentContext.SequenceNo}
        toSend=json.dumps(data)
        self.CurrentContext.socket.send(toSend.encode())
        #sleep(self.CurrentContext.sleep_time)
        return self.CurrentContext.ack()

class FinWait_2(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def fin(self):
        command = self.CurrentContext.socket.recv(1024)
        msg=command.decode()
        a=json.loads(msg)
        b=a["SequenceNo"]
        c=a["acknowledgementNo"]
        if c==self.CurrentContext.SequenceNo:
            self.CurrentContext.SequenceNo=c
            self.CurrentContext.acknowledgementNo=b+1
            print("Received FIN packet...")
            print("Transitioning to TIMEDWAIT state...")
            self.CurrentContext.setState("TIMEDWAIT")
        return True
    def trigger(self):
        return self.CurrentContext.fin()

class TimedWait(State,Transition):
    def __init__(self, Context):
        State.__init__(self,Context)
    def timeout(self):
        print("Transitioning to CLOSED state...")
        self.CurrentContext.setState("CLOSED")
        return True
    def trigger(self):
        sleep(self.CurrentContext.sleep_time)
        print("Sending ACK packet...")
        data={"SequenceNo":self.CurrentContext.SequenceNo,"acknowledgementNo":self.CurrentContext.acknowledgementNo}
        toSend=json.dumps(data)
        self.CurrentContext.socket.send(toSend.encode())
        sleep(self.CurrentContext.sleep_time)
        return self.CurrentContext.timeout()
        
class TCPClient(StateContext, Transition):
    def __init__(self):
        self.sleep_time = 2 #puts pauses in script for demo purposes. Set to 0 if not required
        self.host = "127.0.0.1"
        self.port = 5001
        self.connection_address = 0
        self.socket = None
        self.SequenceNo=random.randint(0,2000)
        self.acknowledgementNo=0
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["SYN_SENT"] = SynSent(self)
        self.availableStates["ESTABLISHED"] = Established(self)
        self.availableStates["FINWAIT1"] = FinWait_1(self)
        self.availableStates["FINWAIT2"] = FinWait_2(self)
        self.availableStates["TIMEDWAIT"] = TimedWait(self)
        print("Transitioning to closed!")
        self.setState("CLOSED")

    def active_open(self):
        return self.CurrentState.active_open()
    def syn_ack(self):
        return self.CurrentState.syn_ack()
    def ack(self):
        return self.CurrentState.ack()
    def rst(self):
        return self.CurrentState.rst()
    def close(self):
        return self.CurrentState.close()
    def fin(self):
        return self.CurrentState.fin()
    def timeout(self):
        return self.CurrentState.timeout()
    
    def make_connection(self):
        '''this method initiates an outbound connection'''
        self.socket = socket()
        self.socket.settimeout(30)
        try:
            self.socket.connect((self.host, self.port))
            self.connection_address = self.host
        except Exception as err:
            print(err)
            exit()

if __name__=='__main__':
    Activeclient=TCPClient()
    Activeclient.active_open()
