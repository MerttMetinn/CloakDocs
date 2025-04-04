import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import traceback

def send_email(to, subject, html_content, text_content=None):
    """
    E-posta gönderme fonksiyonu
    """
    
    # E-posta ayarları
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 465))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    is_secure = os.environ.get('SMTP_SECURE', 'true').lower() == 'true'
    
    # Ayarların kontrolü
    print(f"SMTP Ayarları: {smtp_host}:{smtp_port}, Güvenli: {is_secure}")
    print(f"SMTP Kullanıcı: {smtp_user}")
    print(f"SMTP Şifre: {'*' * len(smtp_password) if smtp_password else 'Yok'}")
    
    # E-posta gönderici
    sender = f"Akademik Makale Sistemi <{smtp_user}>"
    
    # E-posta oluşturma
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    
    # Text versiyonu
    if text_content:
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        msg.attach(part1)
    
    # HTML versiyonu
    part2 = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part2)
    
    try:
        print(f"SMTP bağlantısı kuruluyor: {smtp_host}:{smtp_port}")
        
        # SMTP bağlantısı kurma
        if is_secure:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        
        print("SMTP bağlantısı kuruldu")
        
        # Giriş yapma
        if smtp_user and smtp_password:
            print(f"SMTP giriş yapılıyor: {smtp_user}")
            server.login(smtp_user, smtp_password)
            print("SMTP giriş başarılı")
        
        # E-posta gönderme
        print(f"E-posta gönderiliyor: {to}")
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        
        print("E-posta başarıyla gönderildi")
        return True
    
    except Exception as e:
        print(f"E-posta gönderme hatası: {e}")
        traceback.print_exc()  # Detaylı hata bilgisi
        return False

def send_tracking_number_email(email, tracking_number, file_name):
    """
    Yazara makalesinin takip numarasını içeren bir e-posta gönderir
    """
    subject = "Makale Yükleme Başarılı - Akademik Makale Değerlendirme Sistemi"
    
    # HTML içeriği e-posta şablonundan al
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(base_dir, "templates", "emails", "tracking_number.html")
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Şablon okuma hatası: {e}")
        html_content = """
        <h2>Makale Yükleme Başarılı</h2>
        <p>Sayın Akademisyen,</p>
        <p>Makaleniz başarıyla sistemimize yüklenmiştir. Makalenizin durumunu takip etmek için aşağıdaki takip numarasını kullanabilirsiniz.</p>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="font-weight: bold; margin: 0;">Takip Numaranız:</p>
            <p style="font-size: 18px; font-weight: bold; margin: 10px 0; font-family: monospace;">{tracking_number}</p>
        </div>
        <p>Dosya Adı: {file_name}</p>
        <p>Makalenizin durumunu sorgulamak için <a href="${{BASE_URL}}/author/check-status">bu bağlantıyı</a> ziyaret edebilirsiniz.</p>
        <p>Bu e-posta otomatik olarak gönderilmiştir, lütfen yanıtlamayınız.</p>
        <p>&copy; {{'CURRENT_YEAR'}} Akademik Makale Değerlendirme Sistemi</p>
        """
    
    # Değişkenleri şablona ekle
    html_content = html_content.replace("{tracking_number}", tracking_number)
    html_content = html_content.replace("{file_name}", file_name)
    
    # BASE_URL ve CURRENT_YEAR değişkenlerini değiştir
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    current_year = str(datetime.datetime.now().year)
    
    html_content = html_content.replace("${{BASE_URL}}", base_url)
    html_content = html_content.replace("{{'CURRENT_YEAR'}}", current_year)
    
    # Text içeriği oluştur (HTML alternatifi için)
    text_content = f"""
    Makale Yükleme Başarılı
    
    Sayın Akademisyen,
    
    Makaleniz başarıyla sistemimize yüklenmiştir. Makalenizin durumunu takip etmek için aşağıdaki takip numarasını kullanabilirsiniz.
    
    Takip Numaranız: {tracking_number}
    
    Dosya Adı: {file_name}
    
    Makalenizin durumunu sorgulamak için {base_url}/author/check-status adresini ziyaret edebilirsiniz.
    
    Bu e-posta otomatik olarak gönderilmiştir, lütfen yanıtlamayınız.
    © {current_year} Akademik Makale Değerlendirme Sistemi
    """
    
    print(f"Takip numarası e-postası gönderiliyor: {email}, Takip No: {tracking_number}")
    success = send_email(email, subject, html_content, text_content)
    print(f"E-posta gönderim sonucu: {'Başarılı' if success else 'Başarısız'}")
    
    return success

def send_revision_confirmation_email(email, tracking_number, original_tracking_number, file_name):
    """
    Yazara revize makalesinin başarıyla alındığını bildiren bir e-posta gönderir
    """
    subject = "Revize Makale Alındı - Akademik Makale Değerlendirme Sistemi"
    
    # HTML içeriği e-posta şablonundan al
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(base_dir, "templates", "emails", "revision_confirmation.html")
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Şablon okuma hatası: {e}")
        html_content = """
        <h2>Revize Makale Alındı</h2>
        <p>Sayın Akademisyen,</p>
        <p>Revize ettiğiniz makaleniz başarıyla sistemimize alınmıştır. Revize makalenizin durumunu aşağıdaki bilgilerle takip edebilirsiniz.</p>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="font-weight: bold; margin: 0;">Revize Makale Takip Numarası:</p>
            <p style="font-size: 18px; font-weight: bold; margin: 10px 0; font-family: monospace;">{tracking_number}</p>
            <p style="font-weight: bold; margin: 0;">Orijinal Makale Takip Numarası:</p>
            <p style="font-size: 16px; margin: 10px 0; font-family: monospace;">{original_tracking_number}</p>
        </div>
        <p>Dosya Adı: {file_name}</p>
        <p>Revize makaleniz editörler tarafından incelenecek ve gerekli işlemler yapılacaktır. İnceleme süreci tamamlandığında size bilgi verilecektir.</p>
        <p>Makalenizin durumunu sorgulamak için <a href="${{BASE_URL}}/author/check-status">bu bağlantıyı</a> ziyaret edebilirsiniz.</p>
        <p>Bu e-posta otomatik olarak gönderilmiştir, lütfen yanıtlamayınız.</p>
        <p>&copy; {{'CURRENT_YEAR'}} Akademik Makale Değerlendirme Sistemi</p>
        """
    
    # Değişkenleri şablona ekle
    html_content = html_content.replace("{tracking_number}", tracking_number)
    html_content = html_content.replace("{original_tracking_number}", original_tracking_number)
    html_content = html_content.replace("{file_name}", file_name)
    
    # BASE_URL ve CURRENT_YEAR değişkenlerini değiştir
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    current_year = str(datetime.datetime.now().year)
    
    html_content = html_content.replace("${{BASE_URL}}", base_url)
    html_content = html_content.replace("{{'CURRENT_YEAR'}}", current_year)
    
    # Text içeriği oluştur (HTML alternatifi için)
    text_content = f"""
    Revize Makale Alındı
    
    Sayın Akademisyen,
    
    Revize ettiğiniz makaleniz başarıyla sistemimize alınmıştır. Revize makalenizin durumunu aşağıdaki bilgilerle takip edebilirsiniz.
    
    Revize Makale Takip Numarası: {tracking_number}
    Orijinal Makale Takip Numarası: {original_tracking_number}
    
    Dosya Adı: {file_name}
    
    Revize makaleniz editörler tarafından incelenecek ve gerekli işlemler yapılacaktır. İnceleme süreci tamamlandığında size bilgi verilecektir.
    
    Makalenizin durumunu sorgulamak için {base_url}/author/check-status adresini ziyaret edebilirsiniz.
    
    Bu e-posta otomatik olarak gönderilmiştir, lütfen yanıtlamayınız.
    © {current_year} Akademik Makale Değerlendirme Sistemi
    """
    
    print(f"Revizyon onay e-postası gönderiliyor: {email}, Takip No: {tracking_number}")
    success = send_email(email, subject, html_content, text_content)
    print(f"E-posta gönderim sonucu: {'Başarılı' if success else 'Başarısız'}")
    
    return success 