"""Service d'envoi d'emails avec Gmail OAuth2"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from app.core.config import settings


def get_gmail_service():
    """Créer le service Gmail avec OAuth2."""
    creds = Credentials(
        token=None,
        refresh_token=settings.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
    )
    
    service = build('gmail', 'v1', credentials=creds)
    return service


def send_invitation_email(to_email: str, famille_nom: str, token: str) -> bool:
    """
    Envoyer un email d'invitation via Gmail OAuth2.
    
    Args:
        to_email: Email du destinataire
        famille_nom: Nom de la famille
        token: Token d'invitation
        
    Returns:
        True si envoyé, False sinon
    """
    if not settings.GMAIL_REFRESH_TOKEN:
        print("⚠️  Gmail OAuth2 non configuré, invitation non envoyée")
        return False
    
    try:
        service = get_gmail_service()
        
        # Lien d'invitation
        invitation_url = f"{settings.FRONTEND_URL}/invitation/{token}"
        
        # Corps de l'email en HTML
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #c41e3a 0%, #165b33 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🎄 Liste de Noël</h1>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9;">
                    <h2 style="color: #333;">Vous êtes invité(e) !</h2>
                    <p style="font-size: 16px; color: #555;">
                        Vous avez été invité(e) à rejoindre la famille <strong>{famille_nom}</strong> 
                        pour partager vos listes de cadeaux de Noël ! 🎁
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_url}" 
                           style="background: #c41e3a; color: white; padding: 15px 30px; 
                                  text-decoration: none; border-radius: 5px; font-weight: bold;
                                  display: inline-block;">
                            Accepter l'invitation
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #777;">
                        Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
                        <a href="{invitation_url}" style="color: #c41e3a;">{invitation_url}</a>
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #999; text-align: center;">
                        Vous recevez cet email car quelqu'un vous a invité sur Liste de Noël.<br>
                        Si vous n'attendez pas cette invitation, vous pouvez ignorer cet email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Créer le message
        message = MIMEText(html, 'html')
        message['To'] = to_email
        message['From'] = f"{settings.GMAIL_FROM_NAME} <{settings.GMAIL_FROM_EMAIL}>"
        message['Subject'] = f"🎄 Invitation à rejoindre {famille_nom}"
        
        # Encoder en base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Envoyer via Gmail API
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        print(f"✅ Email envoyé à {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")
        return False