import { Route, Routes } from 'react-router-dom'
import Home from './screens/Home.jsx'
import Session from './screens/Session.jsx'
import Brief from './screens/Brief.jsx'
import Debrief from './screens/Debrief.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/session" element={<Session />} />
      <Route path="/brief" element={<Brief />} />
      <Route path="/debrief" element={<Debrief />} />
    </Routes>
  )
}
