from datetime import datetime
from sqlalchemy.orm import Session
from src.core.database import db
from src.core.models import Chat, Message

class ChatManager:
    def __init__(self):
        pass

    def create_chat(self, title="New Chat", model_name=None):
        """Create a new chat session."""
        session = db.get_session()
        try:
            new_chat = Chat(title=title, model_name=model_name)
            session.add(new_chat)
            session.commit()
            session.refresh(new_chat)
            return new_chat
        except Exception as e:
            session.rollback()
            print(f"Error creating chat: {e}")
            return None
        finally:
            session.close()

    def get_all_chats(self):
        """Retrieve all chats ordered by updated_at desc."""
        session = db.get_session()
        try:
            chats = session.query(Chat).order_by(Chat.updated_at.desc()).all()
            return chats
        finally:
            session.close()

    def get_chat(self, chat_id):
        """Retrieve a specific chat by ID."""
        session = db.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            return chat
        finally:
            session.close()

    def delete_chat(self, chat_id):
        """Delete a chat and its messages."""
        session = db.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                session.delete(chat)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error deleting chat: {e}")
            return False
        finally:
            session.close()

    def add_message(self, chat_id, role, content, thinking=None, content_type='text', images=None):
        """Add a message to a chat."""
        session = db.get_session()
        try:
            new_message = Message(
                chat_id=chat_id,
                role=role,
                content=content,
                thinking=thinking,
                content_type=content_type,
                images=images
            )
            session.add(new_message)
            
            # Update chat timestamp
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.updated_at = datetime.utcnow()
                
            session.commit()
            session.refresh(new_message)
            return new_message
        except Exception as e:
            session.rollback()
            print(f"Error adding message: {e}")
            return None
        finally:
            session.close()

    def get_messages(self, chat_id):
        """Get all messages for a chat."""
        session = db.get_session()
        try:
            messages = session.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
            return messages
        finally:
            session.close()

    def update_chat_title(self, chat_id, new_title):
        """Update the title of a chat."""
        session = db.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.title = new_title
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error updating chat title: {e}")
            return False
        finally:
            session.close()

    def update_chat_model(self, chat_id, model_name):
        """Update the model used for a chat."""
        session = db.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.model_name = model_name
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error updating chat model: {e}")
            return False
        finally:
            session.close()

    def fork_chat(self, original_chat_id, message_id):
        """
        Create a new chat starting with messages up to (and including) message_id from original chat.
        """
        session = db.get_session()
        try:
            original_chat = session.query(Chat).filter(Chat.id == original_chat_id).first()
            if not original_chat:
                return None
            
            # Create new chat
            new_title = f"{original_chat.title} (Fork)"
            new_chat = Chat(title=new_title, model_name=original_chat.model_name)
            session.add(new_chat)
            session.flush() # Get ID
            
            # Copy messages
            messages = session.query(Message).filter(
                Message.chat_id == original_chat_id,
                Message.id <= message_id
            ).order_by(Message.created_at.asc()).all()
            
            for msg in messages:
                new_msg = Message(
                    chat_id=new_chat.id,
                    role=msg.role,
                    content=msg.content,
                    thinking=msg.thinking,
                    content_type=msg.content_type,
                    images=msg.images  # Preserve images when forking
                )
                session.add(new_msg)
            
            session.commit()
            session.refresh(new_chat)
            return new_chat
        except Exception as e:
            session.rollback()
            print(f"Error forking chat: {e}")
            return None
        finally:
            session.close()

    def export_chat(self, chat_id, format='markdown'):
        """Export chat messages to a string."""
        session = db.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            messages = session.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
            
            if format == 'markdown':
                output = f"# {chat.title}\n\n"
                for msg in messages:
                    role = "User" if msg.role == "user" else "Assistant"
                    output += f"**{role}**:\n{msg.content}\n\n---\n\n"
                return output
            elif format == 'json':
                import json
                messages_data = []
                for msg in messages:
                    msg_dict = {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": str(msg.created_at)
                    }
                    # Include thinking if present
                    if msg.thinking:
                        msg_dict["thinking"] = msg.thinking
                    # Include images if present
                    if msg.images:
                        try:
                            msg_dict["images"] = json.loads(msg.images)
                        except (json.JSONDecodeError, TypeError):
                            msg_dict["images"] = msg.images
                    messages_data.append(msg_dict)

                data = {
                    "title": chat.title,
                    "model": chat.model_name,
                    "messages": messages_data
                }
                return json.dumps(data, indent=4)
            return ""
        finally:
            session.close()

    def rename_chat(self, chat_id, new_title):
        """Rename a chat."""
        return self.update_chat_title(chat_id, new_title)

    def import_chat(self, file_path):
        """Import a chat from a JSON file."""
        import json
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            title = data.get('title', 'Imported Chat')
            model_name = data.get('model', 'llama3')
            messages_data = data.get('messages', [])
            
            session = db.get_session()
            try:
                new_chat = Chat(title=title, model_name=model_name)
                session.add(new_chat)
                session.flush()
                
                for msg_data in messages_data:
                    # Parse images back to JSON string if present
                    images_json = None
                    if 'images' in msg_data:
                        try:
                            images_json = json.dumps(msg_data['images']) if isinstance(msg_data['images'], list) else msg_data['images']
                        except Exception as e:
                            print(f"Error parsing images during import: {e}")

                    new_msg = Message(
                        chat_id=new_chat.id,
                        role=msg_data.get('role', 'user'),
                        content=msg_data.get('content', ''),
                        thinking=msg_data.get('thinking'),
                        images=images_json,
                        created_at=datetime.fromisoformat(msg_data.get('timestamp')) if 'timestamp' in msg_data else datetime.utcnow()
                    )
                    session.add(new_msg)
                
                session.commit()
                session.refresh(new_chat)
                return new_chat
            except Exception as e:
                session.rollback()
                print(f"Error importing chat DB: {e}")
                return None
            finally:
                session.close()
                
        except Exception as e:
            print(f"Error reading import file: {e}")
            return None

# Global instance
chat_manager = ChatManager()
