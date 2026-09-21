import {createRoot} from 'react-dom/client';
import {Finanzas} from '../components/crm/finanzas';
import {Inmuebles} from '../components/crm/inmuebles';
import {Agenda} from '../components/crm/agenda';
import {Clientes} from '../components/crm/clientes';
import {Directorio} from '../components/crm/directorio';
import {Espacio} from '../components/broquer/espacio';
import {useRuta} from './navigation';
import '../app/globals.css';
import './mobile.css';
function App(){const ruta=useRuta();const pantallas={'/':'inicio','/agenda':'agenda','/campanas':'campanas','/herramientas':'herramientas','/acceso':'acceso'} as const;const pantalla=pantallas[ruta as keyof typeof pantallas];if(ruta==='/finanzas')return <Finanzas demo/>;if(ruta==='/inmuebles')return <Inmuebles demo/>;if(ruta==='/agenda')return <Agenda demo/>;if(ruta==='/clientes')return <Clientes demo/>;if(ruta==='/directorio')return <Directorio demo/>;return pantalla?<Espacio pantalla={pantalla}/>:<main className="confirmar-contenedor"><h1>Esta pantalla no está disponible.</h1><a href="/">Volver al inicio</a></main>}
createRoot(document.getElementById('root')!).render(<App/>);
