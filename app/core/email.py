"""Service d'envoi d'emails via Gmail OAuth2"""
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings


def send_email(to_email: str, subject: str, html_content: str):
    """
    Envoyer un email via Gmail API.
    
    Args:
        to_email: Destinataire
        subject: Sujet de l'email
        html_content: Contenu HTML de l'email
    """
    # Si les credentials Gmail ne sont pas configurés, ne pas crasher
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_REFRESH_TOKEN:
        print("⚠️  Gmail OAuth2 non configuré - Email non envoyé")
        return False
    
    try:
        # Créer les credentials OAuth2
        creds = Credentials(
            token=None,
            refresh_token=settings.GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET
        )
        
        # Construire le service Gmail
        service = build('gmail', 'v1', credentials=creds)
        
        # Créer le message
        message = MIMEText(html_content, 'html')
        message['To'] = to_email
        message['From'] = f"{settings.GMAIL_FROM_NAME} <{settings.GMAIL_FROM_EMAIL}>"
        message['Subject'] = subject
        
        # Encoder en base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Envoyer
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        print(f"✅ Email envoyé à {to_email}")
        return True
        
    except HttpError as error:
        print(f"❌ Erreur Gmail API: {error}")
        return False
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")
        return False


def send_invitation_email(email: str, famille_nom: str, token: str, inviteur_nom: str):
    """
    Envoyer une invitation à rejoindre une famille.
    
    Args:
        email: Email du destinataire
        famille_nom: Nom de la famille
        token: Token unique d'invitation
        inviteur_nom: Nom de la personne qui invite
    """
    subject = f"🎄 Invitation à rejoindre {famille_nom}"
    
    # URL d'acceptation de l'invitation
    invitation_url = f"{settings.FRONTEND_URL}/invitation/{token}"
    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #c41e3a 0%, #165b33 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">🎄 Liste de Noël</h1>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333;">Vous êtes invité(e) ! 🎁</h2>
                <p style="font-size: 16px; color: #555;">
                    <strong>{inviteur_nom}</strong> vous invite à rejoindre la famille 
                    <strong style="color: #c41e3a; font-size: 20px;">"{famille_nom}"</strong> 
                    pour partager vos listes de cadeaux de Noël ! 🎅
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_url}" 
                       style="background: #c41e3a; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; font-weight: bold;
                              display: inline-block; font-size: 16px;">
                        🎁 Accepter l'invitation
                    </a>
                </div>
                
                <div style="background: #fff; border-left: 4px solid #165b33; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #555;">
                        <strong>Famille :</strong> {famille_nom}<br>
                        <strong>Que faire ?</strong> Ajoutez vos cadeaux et voyez ceux de votre famille !
                    </p>
                </div>
                
                <p style="font-size: 14px; color: #777;">
                    Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
                    <a href="{invitation_url}" style="color: #c41e3a; word-break: break-all;">{invitation_url}</a>
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #999; text-align: center;">
                    Vous recevez cet email car {inviteur_nom} vous a invité à rejoindre sa famille sur Liste de Noël.<br>
                    Si vous n'attendez pas cette invitation, vous pouvez ignorer cet email en toute sécurité.
                </p>
            </div>
        </body>
    </html>
    """
    
    return send_email(email, subject, html)


def send_demande_adhesion_email(
    createur_email: str,
    createur_nom: str,
    demandeur_nom: str,
    demandeur_email: str,
    famille_nom: str,
    message_demande: str,
    famille_id: int
):
    """
    Envoyer un email au créateur d'une famille quand quelqu'un demande à la rejoindre.
    """
    subject = f"🎄 Nouvelle demande pour rejoindre {famille_nom}"
    
    # URL pour gérer la demande
    famille_url = f"{settings.FRONTEND_URL}/familles/{famille_id}"
    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #c41e3a 0%, #165b33 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">🎄 Liste de Noël</h1>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333;">Bonjour {createur_nom} ! 👋</h2>
                
                <div style="background: white; border-left: 4px solid #165b33; padding: 20px; margin: 20px 0;">
                    <p style="margin: 0 0 10px 0; font-size: 16px;">
                        <strong>{demandeur_nom}</strong> souhaite rejoindre votre famille <strong>"{famille_nom}"</strong>
                    </p>
                    <p style="margin: 5px 0; color: #666; font-size: 14px;">
                        📧 {demandeur_email}
                    </p>
                </div>
                
                {f'''
                <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; font-style: italic; color: #856404;">
                        💬 Message : "{message_demande}"
                    </p>
                </div>
                ''' if message_demande else ''}
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{famille_url}" 
                       style="background: #c41e3a; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; font-weight: bold;
                              display: inline-block; font-size: 16px;">
                        👀 Voir la demande et répondre
                    </a>
                </div>
                
                <div style="background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 14px; color: #1565c0;">
                        💡 <strong>Astuce :</strong> Connectez-vous sur Liste de Noël et allez dans votre famille "{famille_nom}" 
                        pour accepter ou refuser cette demande.
                    </p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #999; text-align: center;">
                    Vous recevez cet email car quelqu'un a demandé à rejoindre votre famille sur Liste de Noël.<br>
                    Si vous n'êtes pas concerné, vous pouvez ignorer cet email en toute sécurité.
                </p>
            </div>
        </body>
    </html>
    """
    
    return send_email(createur_email, subject, html)