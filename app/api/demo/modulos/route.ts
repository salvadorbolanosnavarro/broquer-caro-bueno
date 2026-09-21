import modulos from "@/shared/modulos.json";
export function GET(){return Response.json({modo:"demo",modulos},{headers:{"Cache-Control":"no-store"}})}
