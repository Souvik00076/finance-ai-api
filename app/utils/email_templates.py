def generate_verification_template(email: str, redirect_uri: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Verify Your Email — Spendly</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0a0a0a; padding: 40px 0;">
    <tr>
      <td align="center">

        <table role="presentation" width="520" cellpadding="0" cellspacing="0" border="0" style="max-width: 520px; width: 100%; background-color: #141414; border-radius: 16px; border: 1px solid #1f1f1f; overflow: hidden;">

          <tr>
            <td style="padding: 36px 40px 24px 40px; text-align: center;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display: inline-table;">
                <tr>
                  <td style="background-color: #0d1f17; border-radius: 10px; padding: 10px 12px; vertical-align: middle;">
                    <span style="color: #2dd4a0; font-size: 18px; font-weight: 700;">S</span>
                  </td>
                  <td style="padding-left: 10px; vertical-align: middle;">
                    <span style="color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.3px;">Spendly</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding: 0 40px;">
              <div style="height: 1px; background-color: #1f1f1f;"></div>
            </td>
          </tr>

          <tr>
            <td style="padding: 32px 40px 12px 40px; text-align: center;">
              <div style="display: inline-block; background-color: #0d1f17; border-radius: 50%; width: 56px; height: 56px; line-height: 56px; text-align: center; margin-bottom: 24px;">
                <span style="font-size: 26px;">✉️</span>
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding: 0 40px; text-align: center;">
              <h1 style="margin: 0 0 12px 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: -0.4px;">
                Verify your email
              </h1>
              <p style="margin: 0 0 8px 0; color: #888888; font-size: 15px; line-height: 1.6;">
                You're almost there! We just need to confirm that
              </p>
              <p style="margin: 0 0 8px 0; color: #2dd4a0; font-size: 15px; font-weight: 600;">
                {email}
              </p>
              <p style="margin: 0 0 32px 0; color: #888888; font-size: 15px; line-height: 1.6;">
                belongs to you. Click the button below to verify your email and start tracking expenses effortlessly.
              </p>
            </td>
          </tr>

          <tr>
            <td style="padding: 0 40px 32px 40px; text-align: center;">
              <a href="{redirect_uri}" target="_blank" style="display: inline-block; background-color: #2dd4a0; color: #0a0a0a; text-decoration: none; font-size: 15px; font-weight: 700; padding: 14px 36px; border-radius: 10px; letter-spacing: 0.2px;">
                Verify Email&nbsp;&nbsp;→
              </a>
            </td>
          </tr>

          <tr>
            <td style="padding: 0 40px;">
              <div style="height: 1px; background-color: #1f1f1f;"></div>
            </td>
          </tr>

          <tr>
            <td style="padding: 24px 40px; text-align: center;">
              <p style="margin: 0; color: #555555; font-size: 13px; line-height: 1.6;">
                ⏱ This link expires in <span style="color: #888888; font-weight: 600;">24 hours</span>. If you didn't create a Spendly account, you can safely ignore this email.
              </p>
            </td>
          </tr>

          <tr>
            <td style="padding: 0 40px;">
              <div style="height: 1px; background-color: #1f1f1f;"></div>
            </td>
          </tr>

          <tr>
            <td style="padding: 24px 40px 32px 40px; text-align: center;">
              <p style="margin: 0 0 4px 0; color: #333333; font-size: 12px;">
                © 2026 Spendly. Track expenses effortlessly.
              </p>
              <p style="margin: 0; color: #333333; font-size: 12px;">
                Powered by WhatsApp&nbsp;&nbsp;·&nbsp;&nbsp;Built with ❤️
              </p>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

</body>
</html>"""
