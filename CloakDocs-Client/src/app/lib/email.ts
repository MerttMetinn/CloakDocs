import nodemailer from 'nodemailer';

// E-posta gönderici yapılandırması
const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: parseInt(process.env.SMTP_PORT || '587'),
  secure: process.env.SMTP_SECURE === 'true',
  auth: {
    user: process.env.SMTP_USER || '',
    pass: process.env.SMTP_PASSWORD || '',
  },
});

interface SendEmailParams {
  to: string;
  subject: string;
  html: string;
  text?: string;
}

/**
 * E-posta gönderme fonksiyonu
 */
export async function sendEmail({ to, subject, html, text }: SendEmailParams): Promise<boolean> {
  try {
    const info = await transporter.sendMail({
      from: `"Akademik Makale Sistemi" <${process.env.SMTP_USER}>`,
      to,
      subject,
      html,
      text,
    });

    console.log('E-posta gönderildi:', info.messageId);
    return true;
  } catch (error) {
    console.error('E-posta gönderme hatası:', error);
    return false;
  }
}

/**
 * Takip numarası e-postası gönderme
 */
export async function sendTrackingNumberEmail(
  email: string,
  trackingNumber: string,
  fileName: string
): Promise<boolean> {
  const subject = 'Makale Yükleme - Takip Numarası';
  
  const html = `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
      <h2 style="color: #003366; border-bottom: 1px solid #e0e0e0; padding-bottom: 10px;">Makale Yükleme Başarılı</h2>
      
      <p style="color: #333333; font-size: 16px; line-height: 1.5;">
        Sayın Akademisyen,
      </p>
      
      <p style="color: #333333; font-size: 16px; line-height: 1.5;">
        Makaleniz başarıyla sistemimize yüklenmiştir. Makalenizin durumunu takip etmek için aşağıdaki takip numarasını kullanabilirsiniz.
      </p>
      
      <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
        <p style="font-size: 14px; color: #666666; margin-bottom: 5px;">Takip Numaranız:</p>
        <p style="font-size: 24px; font-weight: bold; color: #003366; font-family: monospace; margin: 0;">${trackingNumber}</p>
      </div>
      
      <p style="color: #333333; font-size: 16px; line-height: 1.5;">
        <strong>Dosya Adı:</strong> ${fileName}
      </p>
      
      <p style="color: #333333; font-size: 16px; line-height: 1.5;">
        Makalenizin durumunu sorgulamak için <a href="${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/author/check-status" style="color: #008080; text-decoration: none; font-weight: bold;">Makale Durumu Sorgulama</a> sayfasını ziyaret edebilirsiniz.
      </p>
      
      <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666666; font-size: 14px;">
        <p>Bu e-posta otomatik olarak gönderilmiştir, lütfen yanıtlamayınız.</p>
        <p>© ${new Date().getFullYear()} Akademik Makale Değerlendirme Sistemi</p>
      </div>
    </div>
  `;
  
  return sendEmail({ to: email, subject, html });
}

/**
 * Bildirim e-postası gönderme
 */
export async function sendNotificationEmail({
  to,
  subject,
  text,
  html
}: SendEmailParams): Promise<boolean> {
  return sendEmail({ to, subject, html, text });
} 