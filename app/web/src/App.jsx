import { Route, Routes } from 'react-router-dom'
import Dojo from './components/Dojo.jsx'
import RailMedia from './components/RailMedia.jsx'
import Home from './screens/Home.jsx'
import Session from './screens/Session.jsx'

function Stub({ name, stem }) {
  return (
    <Dojo rail={
      <RailMedia stem={stem}>
        <p className="font-serif italic text-washi">Kurosawa waits.</p>
      </RailMedia>
    }>
      <h1 className="font-serif text-2xl">{name}</h1>
    </Dojo>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/session" element={<Session />} />
      <Route path="/brief" element={<Stub name="Brief" stem="brief-sensei" />} />
      <Route path="/debrief" element={<Stub name="Debrief" stem="debrief-runner" />} />
    </Routes>
  )
}
