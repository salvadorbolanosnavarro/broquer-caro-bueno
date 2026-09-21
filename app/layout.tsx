import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {title:"Broquer · Tu espacio de trabajo",referrer:"no-referrer",description:"Herramientas para el día a día del asesor inmobiliario.",icons:{icon:"/favicon.svg"}};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="es-MX"><body>{children}</body></html>}
