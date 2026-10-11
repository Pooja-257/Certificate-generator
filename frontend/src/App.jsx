import { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard.jsx";
import CreateJob from "./components/CreateJob.jsx";
import JobDetails from "./components/JobDetails.jsx";

// Tiny hash router: "#/", "#/new", "#/jobs/12". Avoids a routing dependency.
function useHashRoute() {
  const read = () => window.location.hash.replace(/^#/, "") || "/";
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => setRoute(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  const jobMatch = route.match(/^\/jobs\/(\d+)$/);

  let page = <Dashboard />;
  if (route === "/new") page = <CreateJob />;
  else if (jobMatch) page = <JobDetails key={jobMatch[1]} jobId={Number(jobMatch[1])} />;

  return (
    <>
      <header className="topbar">
        <a href="#/" className="brand">
          <span className="brand-seal" aria-hidden="true" />
          Certificate Batches
        </a>
        <a href="#/new" className="btn btn-primary">New batch</a>
      </header>
      <main className="page">{page}</main>
    </>
  );
}
