export default function ResearchAnswers() {
  return (
    <section className="research" id="research" aria-labelledby="research-title">
      <h2 id="research-title">The research questions, answered</h2>
      <p className="step-lead">Short answers backed by what the steps above demonstrate.</p>

      <article className="qa" id="q-structure">
        <h3>What is the structure of a JWT?</h3>
        <p>
          Three base64url-encoded parts joined by dots: <code>header.payload.signature</code> (defined in{" "}
          <a href="https://www.rfc-editor.org/rfc/rfc7519.html">RFC 7519</a>).
        </p>
        <div className="anatomy">
          <div className="anatomy-part anatomy-h">
            <strong>Header</strong>
            <code>{'{"alg": "HS256", "typ": "JWT"}'}</code>
            <span>Which algorithm signed the token.</span>
          </div>
          <div className="anatomy-part anatomy-p">
            <strong>Payload</strong>
            <code>{'{"user_id": "1", "token_type": "access", "iat": …, "exp": …, "jti": "…"}'}</code>
            <span>Claims: who you are, when it was issued, when it expires, a unique ID.</span>
          </div>
          <div className="anatomy-part anatomy-s">
            <strong>Signature</strong>
            <code>HMAC-SHA256(secret, header + "." + payload)</code>
            <span>Proves the server made it and nothing was changed.</span>
          </div>
        </div>
        <p>
          The payload is encoded, not encrypted: anyone holding the token can read it, so it never contains a
          password. Changing a single character of the header or payload breaks the signature, and the server answers
          401. Without the secret key nobody can make a new valid signature.
        </p>
      </article>

      <article className="qa" id="q-tokens">
        <h3>What is the difference between an access token and a refresh token?</h3>
        <div className="table-wrap">
          <table className="compare-table">
            <thead>
              <tr>
                <th scope="col" />
                <th scope="col">Access token</th>
                <th scope="col">Refresh token</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Job</th>
                <td>Proves who you are on every API request</td>
                <td>Gets a new access token without the password</td>
              </tr>
              <tr>
                <th scope="row">Lifetime here</th>
                <td>5 minutes</td>
                <td>1 day</td>
              </tr>
              <tr>
                <th scope="row">Sent to</th>
                <td>Every protected endpoint, as <code>Authorization: Bearer …</code></td>
                <td>Only <code>/api/auth/refresh/</code> and <code>/api/auth/logout/</code></td>
              </tr>
              <tr>
                <th scope="row">How the server checks it</th>
                <td>Signature and expiry only, no database lookup</td>
                <td>Signature, expiry and the blacklist table</td>
              </tr>
              <tr>
                <th scope="row">Can it be revoked?</th>
                <td>No, it works until it expires</td>
                <td>Yes, blacklisted at logout and after each rotation</td>
              </tr>
              <tr>
                <th scope="row">If stolen</th>
                <td>Usable for at most 5 minutes</td>
                <td>Usable once at most: rotation blacklists it on use</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Two tokens give a balance: the one sent everywhere is short-lived, so a leak does little harm, and the
          long-lived one is used rarely and can be cancelled. Using one as the other is refused (step 4).
        </p>
      </article>

      <article className="qa" id="q-sessions">
        <h3>JWT vs session authentication: where is each stored, and what are the risks?</h3>
        <div className="table-wrap">
          <table className="compare-table">
            <thead>
              <tr>
                <th scope="col" />
                <th scope="col">JWT</th>
                <th scope="col">Session</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Where login state lives</th>
                <td>In the token itself, held by the client</td>
                <td>On the server, in Django's session table</td>
              </tr>
              <tr>
                <th scope="row">What the browser keeps</th>
                <td>The token: in memory, localStorage or a cookie</td>
                <td>A random <code>sessionid</code> in an HttpOnly cookie</td>
              </tr>
              <tr>
                <th scope="row">XSS (injected script)</th>
                <td className="bad">Token in localStorage can be stolen and used anywhere</td>
                <td className="good">HttpOnly cookie cannot be read by scripts</td>
              </tr>
              <tr>
                <th scope="row">CSRF (forged request from another site)</th>
                <td className="good">Not sent automatically, so not exposed</td>
                <td className="bad">Cookie sent automatically; needs a CSRF token</td>
              </tr>
              <tr>
                <th scope="row">Logout</th>
                <td className="bad">Refresh token blacklisted; access token works until expiry</td>
                <td className="good">Session deleted; cookie useless at once</td>
              </tr>
              <tr>
                <th scope="row">Tampering</th>
                <td className="good">Signature check rejects any change</td>
                <td className="good">Random ID; nothing to edit</td>
              </tr>
              <tr>
                <th scope="row">Server work per request</th>
                <td>Verify a signature, no lookup</td>
                <td>Look up the session in the database</td>
              </tr>
              <tr>
                <th scope="row">Suits</th>
                <td>Mobile apps, APIs, several servers</td>
                <td>Classic websites on one domain</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          In short, JWT trades instant logout for stateless checks and freedom from CSRF; sessions make the opposite
          trade. Steps 5 and 6 show both sides live.
        </p>
      </article>

    </section>
  );
}
