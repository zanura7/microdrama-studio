import "./globals.css";

export const metadata = {
  title: "MicroDrama AI — Agentic Micro-Drama Generator",
  description:
    "Transform any idea into a complete cinematic video using a multi-agent AI pipeline powered by MuAPI.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                if (localStorage.getItem('microdrama_theme') === 'dark') {
                  document.documentElement.classList.add('dark');
                }
              } catch(e) {}

              // Prevent browser extension errors (e.g. Urban VPN / content scripts) from crashing Next.js dev overlay
              if (typeof window !== 'undefined') {
                window.addEventListener('error', function(e) {
                  var src = e.filename || (e.error && e.error.stack) || '';
                  if (
                    src.includes('chrome-extension://') ||
                    src.includes('moz-extension://') ||
                    src.includes('eppiocemhmnlbhjplcgkofciiegomcon') ||
                    (e.message && e.message.includes('M_ID'))
                  ) {
                    e.stopImmediatePropagation();
                    e.preventDefault();
                    return true;
                  }
                }, true);

                window.addEventListener('unhandledrejection', function(e) {
                  var reason = e.reason;
                  var str = (reason && (reason.stack || reason.message || String(reason))) || '';
                  if (
                    str.includes('chrome-extension://') ||
                    str.includes('moz-extension://') ||
                    str.includes('eppiocemhmnlbhjplcgkofciiegomcon') ||
                    str.includes('M_ID')
                  ) {
                    e.stopImmediatePropagation();
                    e.preventDefault();
                  }
                }, true);
              }
            `,
          }}
        />
      </head>
      <body className="antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
