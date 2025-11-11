from atproto import Client, IdResolver, models
from time import sleep, time
import sqlite3


USERNAME = 'username-here'
PASSWORD = 'password-here' 


def get_users_in_db(cur, did):
        res = cur.execute("SELECT * FROM user where did=?", (did,))
        output = res.fetchall()
        return output

def add_to_table(cur,con,name,data):
    if name == 'user':
        cur.executemany(f"INSERT INTO {name} VALUES(?, ?, ?)", data)
    else:
        cur.executemany(f"INSERT INTO {name} VALUES(?, ?, ?, ?, ?)", data)
    con.commit
    return "done"

def get_convo_for_did(dm,did):
    convo_list = dm.list_convos()
    for convo in convo_list.convos:
        mess=dm.get_messages({'convo_id': convo.id}).messages
        #print("og did: "+str(did))
        for i in range(min(len(mess),10)):
            user_did=mess[i].sender.did
            #print(user_did)
            if str(did) in str(user_did):
                return convo
            
def send_chat_message(dm,did,text):
    convo=get_convo_for_did(dm,did)
    message = dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo.id,
            message=models.ChatBskyConvoDefs.MessageInput(
                text=text,
            ),
        )
    )
    return message

intro_message="""this is random chat, this is how to use the bot:

- send "!connect" to connect to a chat. 
(the other person will not see anything about you, they will only see the messages you send after the bot sends "random person connected")

- send "!disconnect" to disconnect from a chat. 
(the other person will not see "!disconnect", the other person will see "other person left chat")"""

youleft_message="""you left the chat.

- send "!connect" to connect to a chat. 
(the other person will not see anything about you, they will only see the messages you send after the bot sends "random person connected")

- send "!disconnect" to disconnect from a chat. 
(the other person will not see "!disconnect", the other person will see "other person left chat")"""

strangerleft_message="""random person left.

- send "!connect" to connect to a chat. 
(the other person will not see anything about you, they will only see the messages you send after the bot sends "random person connected")

- send "!disconnect" to disconnect from a chat. 
(the other person will not see "!disconnect", the other person will see "other person left chat")"""

def main():
    database_con = sqlite3.connect('data4.db')
    database_cur = database_con.cursor()
    res = database_cur.execute("SELECT name FROM sqlite_master")
    if res.fetchone() is None:
        database_cur.execute("CREATE TABLE user(did,inchat,starttime)")
        database_cur.execute("CREATE TABLE chats(chatdid1,chatdid2,did1,did2,starttime)")
        print("made tables")
    client = Client()
    client.login(USERNAME, PASSWORD)
    temp_messages=[]
    while True:
        dm_client = client.with_bsky_chat_proxy()
        dm = dm_client.chat.bsky.convo

        convo_list = dm.list_convos() 
        print(f'Your conversations ({len(convo_list.convos)}):')

        for convo in convo_list.convos:
            members = ', '.join(member.display_name for member in convo.members)
            print(f'- ID: {convo.id} ({members})')

        database_cur.execute("SELECT * FROM chats ORDER BY starttime ASC")
        chats=database_cur.fetchall()
        for i in range(len(chats)):
            convo_dids=[chats[i][0],chats[i][1]]
            user_dids=[chats[i][2],chats[i][3]]
            for i in range(len(user_dids)):
                other=0
                if i == 1:
                    other=0
                else:
                    other=1
                comparing_date=(((dm.get_messages({'convo_id': convo_dids[i]}).messages[0].sent_at).split("T"))[1].replace(":", "")) > (((dm.get_messages({'convo_id': convo_dids[other]}).messages[0].sent_at).split("T"))[1].replace(":", ""))
                recent_messages_dontmatch1=(dm.get_messages({'convo_id': convo_dids[i]}).messages[0].text) != (dm.get_messages({'convo_id': convo_dids[other]}).messages[0].text)
                if 'did:plc:'+user_dids[i] == str(dm.get_messages({'convo_id': convo_dids[i]}).messages[0].sender.did) and recent_messages_dontmatch1 and comparing_date:
                    text=dm.get_messages({'convo_id': convo_dids[i]}).messages[0].text
                    if text == '!disconnect':
                        dm.send_message(
                            models.ChatBskyConvoSendMessage.Data(
                                convo_id=convo_dids[i],
                                message=models.ChatBskyConvoDefs.MessageInput(
                                    text=youleft_message,
                                ),
                            )
                        )
                        dm.send_message(
                            models.ChatBskyConvoSendMessage.Data(
                                convo_id=convo_dids[other],
                                message=models.ChatBskyConvoDefs.MessageInput(
                                    text=strangerleft_message,
                                ),
                            )
                        )
                        database_cur.execute("DELETE FROM chats WHERE did1=:text1 AND did2=:text2", {'text1': user_dids[0], 'text2': user_dids[1]})
                        database_cur.execute("DELETE FROM user WHERE did IN (:text1,:text2)", {'text1': user_dids[0], 'text2': user_dids[1]})
                        database_con.commit()
                    else:
                        dm.send_message(
                            models.ChatBskyConvoSendMessage.Data(
                                convo_id=convo_dids[other],
                                message=models.ChatBskyConvoDefs.MessageInput(
                                    text=text,
                                ),
                            )
                        )



        

        for convo in convo_list.convos:
            memeber=convo.members[0]
            with_plc_did=(str(memeber.did).replace("did:plc:",""))
            if len(get_users_in_db(database_cur, with_plc_did)) == 0:
                convo=get_convo_for_did(dm,memeber.did)
                intro = dm.get_messages({'convo_id': convo.id}).messages
                has_it=False
                for i in range(min(len(intro),10)):
                    if "!connect" == str(intro[i].text):
                        has_it=3
                        break
                    elif "!disconnect" == str(intro[i].text):
                        has_it=True
                        break
                    elif strangerleft_message == str(intro[i].text):
                        has_it=True
                        break
                    elif intro_message == str(intro[i].text):
                        has_it=True
                        break

                print("has it: "+str(has_it))
                if has_it is False:
                    send=send_chat_message(dm,memeber.did,intro_message)
                    print("message sent")
                elif has_it == 3:
                    database_cur.execute("SELECT * FROM user WHERE did=?", (with_plc_did,))
                    output = database_cur.fetchall()
                    if len(output) == 0:
                        data=[[with_plc_did,False,int(time())]]
                        add_to_table(database_cur,database_con,"user",data)
                        database_con.commit()
                        print("added to table")
        
            else:
               database_cur.execute("SELECT * FROM user WHERE did=?", (with_plc_did,))
               output = database_cur.fetchall()
               if len(output) != 0:
                   data=output[0]
                   if data[1] == 0:
                        database_cur.execute("SELECT * FROM user WHERE inchat=:num AND did!=:data ORDER BY starttime ASC", {'num': 0, 'data': with_plc_did})
                        output1 = database_cur.fetchone()
                        if output1 is not None:
                            other_person=output1[0]
                            database_cur.execute("UPDATE user SET inchat=1 WHERE did IN (:og,:other)", {'og': with_plc_did, 'other': other_person})
                            convo_did1=get_convo_for_did(dm,with_plc_did).id
                            convo_did2=get_convo_for_did(dm,other_person).id
                            message = dm.send_message(
                                models.ChatBskyConvoSendMessage.Data(
                                    convo_id=convo_did1,
                                    message=models.ChatBskyConvoDefs.MessageInput(
                                        text="random person connected",
                                    ),
                                )
                            )
                            message = dm.send_message(
                                models.ChatBskyConvoSendMessage.Data(
                                    convo_id=convo_did2,
                                    message=models.ChatBskyConvoDefs.MessageInput(
                                        text="random person connected",
                                    ),
                                )
                            )
                            data=[[convo_did1,convo_did2,with_plc_did,other_person,int(time())]]
                            add_to_table(database_cur,database_con,"chats",data)
                            database_con.commit()
                        database_cur.execute("SELECT starttime FROM user where did=?", (with_plc_did,))
                        user_starttime = database_cur.fetchone()
                        time_waiting = (int(time()) - user_starttime[0])/60 #time waiting in minutes
                        #print(time_waiting)
                   #print(data[1])
                   
                     
        sleep(5)


if __name__ == '__main__':
    main()
