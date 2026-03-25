import "./globals.css";
import type { ReactNode } from "react";

import { AppShell } from "../components/app-shell";
import { AuthProvider } from "../components/auth-provider";
import { getFirebaseWebConfig } from "../lib/firebase-config";

export const metadata = {
  title: "BOQ AUTO Web",
  description: "Kenyan construction estimating and price intelligence platform.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const firebaseConfig = getFirebaseWebConfig();

  return (
    <html lang="en">
      <body>
        <AuthProvider firebaseConfig={firebaseConfig}>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
