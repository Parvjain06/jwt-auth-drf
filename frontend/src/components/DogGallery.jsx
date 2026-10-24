import { useState } from "react";
import { api } from "../lib/api.js";
import StatusBadge from "./StatusBadge.jsx";

const PAGE_SIZE = 9;

function imageFor(breed) {
  if (breed.image_url) return breed.image_url;
  if (breed.reference_image_id) return `https://cdn2.thedogapi.com/images/${breed.reference_image_id}.jpg`;
  return null;
}

function DogCard({ breed }) {
  const [broken, setBroken] = useState(false);
  const src = imageFor(breed);
  return (
    <article className="dog">
      <div className="dog-photo">
        {src && !broken ? (
          <img src={src} alt={breed.name} loading="lazy" onError={() => setBroken(true)} />
        ) : (
          <span className="dog-photo-missing">No photo</span>
        )}
      </div>
      <div className="dog-text">
        <h3>{breed.name}</h3>
        {breed.temperament && <p className="dog-temperament">{breed.temperament}</p>}
        <dl className="dog-facts">
          {breed.breed_group && (
            <>
              <dt>Group</dt>
              <dd>{breed.breed_group}</dd>
            </>
          )}
          {breed.life_span && (
            <>
              <dt>Life span</dt>
              <dd>{breed.life_span}</dd>
            </>
          )}
          {breed.weight_kg && (
            <>
              <dt>Weight</dt>
              <dd>{breed.weight_kg} kg</dd>
            </>
          )}
        </dl>
      </div>
    </article>
  );
}

export default function DogGallery({ access }) {
  const [page, setPage] = useState(0);
  const [breeds, setBreeds] = useState([]);
  const [last, setLast] = useState(null); // { status, detail }
  const [loading, setLoading] = useState(false);

  async function load(p) {
    setLoading(true);
    const res = await api(`/api/dogs/breeds/?limit=${PAGE_SIZE}&page=${p}`, {
      token: access ?? null,
      label: access ? "Fetch dog breeds" : "Fetch dog breeds without a token",
    });
    setLoading(false);
    setLast({ status: res.status, detail: res.data?.detail });
    if (res.ok) {
      setBreeds(res.data.results);
      setPage(p);
    } else {
      setBreeds([]);
    }
  }

  let explain = null;
  if (last && !String(last.status).startsWith("2")) {
    if (last.status === 401 && !access) explain = "No token was sent, so the API refused the request.";
    else if (last.status === 401)
      explain = "The access token was rejected. It has probably expired: use Refresh tokens in step 1.";
    else explain = last.detail;
  }

  return (
    <div className="panel">
      <div className="row between">
        <div className="row">
          <button className="btn btn-primary" onClick={() => load(0)} disabled={loading}>
            {loading ? "Loading…" : access ? "Load dog breeds" : "Try without logging in"}
          </button>
          {breeds.length > 0 && (
            <>
              <button className="btn btn-quiet" onClick={() => load(page - 1)} disabled={loading || page === 0}>
                Previous
              </button>
              <button className="btn btn-quiet" onClick={() => load(page + 1)} disabled={loading}>
                Next
              </button>
              <span className="muted">Page {page + 1}</span>
            </>
          )}
        </div>
        {last && <StatusBadge status={last.status} />}
      </div>

      {explain && <p className="notice notice-bad">{explain}</p>}

      {breeds.length > 0 ? (
        <div className="dogs">
          {breeds.map((b) => (
            <DogCard key={b.id} breed={b} />
          ))}
        </div>
      ) : (
        !explain && (
          <p className="empty-inline">
            {access
              ? "Load the breeds to call the protected endpoint with your access token."
              : "You are not logged in. Try anyway to see the API refuse you."}
          </p>
        )
      )}
    </div>
  );
}
