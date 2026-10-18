import { Link } from "react-router-dom";

export function Guide({ signedIn }: { signedIn: boolean }) {
  return (
    <main className="guide">
      <header className="guide-bar">
        <div className="mark">
          <i>
            <span />
            <span />
            <span />
          </i>
          Request Desk
        </div>
        <Link className="btn primary" to={signedIn ? "/" : "/login"}>
          {signedIn ? "Back to the desk" : "Sign in"}
        </Link>
      </header>

      <article className="guide-wrap">
        <p className="kicker">User guide</p>
        <h1>How to use Request Desk</h1>
        <p className="guide-lead">
          This page is open to everyone. You do not need to sign in to read it. Sign in only when you want to open the
          queue itself.
        </p>

        <nav className="guide-toc" aria-label="Guide contents">
          <a href="#sign-in">1. Sign in</a>
          <a href="#queue">2. Read the queue</a>
          <a href="#reasons">3. See why a person is needed</a>
          <a href="#table">4. Work through the request table</a>
          <a href="#case">5. Open one request</a>
          <a href="#upload">6. Upload and download</a>
        </nav>

        <section className="guide-step" id="sign-in">
          <h2>1. Sign in</h2>
          <p>
            The queue, the request table, and the rules sit behind the sign-in page. Choose <strong>Sign in</strong> at
            the top of this guide, enter the desk username and password, then choose <strong>Enter the desk</strong>.
          </p>
          <figure>
            <img src="/guide/signin.png" alt="The Request Desk sign-in page, with the username and password fields." />
            <figcaption>The sign-in page. The guide you are reading stays available without this step.</figcaption>
          </figure>
        </section>

        <section className="guide-step" id="queue">
          <h2>2. Read the queue</h2>
          <p>
            After you sign in, the first screen is <strong>Request queue</strong>. The four numbers across the top tell
            you how many requests are stored, how many need a person, how many match their category, and how many are
            missing information. Choose a number to open that set of requests.
          </p>
          <figure>
            <img src="/guide/desk.png" alt="The request queue, with counts, categories, priorities, and reasons." />
            <figcaption>The queue. Categories are on the left. Reasons and rules are on the right.</figcaption>
          </figure>
        </section>

        <section className="guide-step" id="reasons">
          <h2>3. See why a person is needed</h2>
          <p>
            On the right of the queue, <strong>Why a person is needed</strong> lists each cause and how many requests
            have it. Examples are High priority, a sensitive phrase, a missing field, or a request that is already
            completed.
          </p>
          <ol>
            <li>Find the cause you want, such as High priority.</li>
            <li>Select that row.</li>
            <li>Read the short explanation that opens under the row.</li>
          </ol>
          <p>
            Under that list, <strong>Rules in force</strong> shows the category rules in the order the desk uses them.
            The keywords for each rule sit on the line below the category name.
          </p>
        </section>

        <section className="guide-step" id="table">
          <h2>4. Work through the request table</h2>
          <p>
            Choose <strong>Requests</strong> in the left menu, or <strong>Open requests</strong> on the queue. The table
            shows one row for each request. The column <strong>Human intervention needed?</strong> is only Yes or No.
            The long explanation is not in the table.
          </p>
          <ol>
            <li>Use the search box for an ID, a role, a summary, or a category.</li>
            <li>Use Needs a person, Clear, Missing information, or the category buttons to narrow the list.</li>
            <li>Use the menus underneath for category, priority, status, and channel.</li>
          </ol>
          <figure>
            <img src="/guide/requests.png" alt="The request table with Yes and No in the human intervention column." />
            <figcaption>Yes means a person should look. No means no review rule was triggered.</figcaption>
          </figure>
        </section>

        <section className="guide-step" id="case">
          <h2>5. Open one request</h2>
          <p>Select a request ID. A card opens in the centre of the screen.</p>
          <ol>
            <li>
              A red heading, <strong>A person must see this</strong>, means review is required. A green heading means no
              person is needed.
            </li>
            <li>
              Read <strong>Why human intervention is needed</strong> first. Each reason is numbered.
            </li>
            <li>Below that, read the suggested acknowledgement, the summary, and the other fields.</li>
            <li>Choose <strong>Close</strong> to return to the table.</li>
          </ol>
          <figure>
            <img src="/guide/case.png" alt="The request card for REQ-004, with three reasons a person must see it." />
            <figcaption>REQ-004 needs a person for three reasons: high priority, finance, and expenses.</figcaption>
          </figure>
        </section>

        <section className="guide-step" id="upload">
          <h2>6. Upload and download</h2>
          <p>On the request table, the buttons along the top move requests in and out of the desk.</p>
          <ol>
            <li>
              <strong>Download view</strong> saves the rows you are looking at now.
            </li>
            <li>
              <strong>Download all</strong> saves every stored request, including the review result.
            </li>
            <li>
              <strong>Re-run analysis</strong> checks the stored requests again with the current rules.
            </li>
            <li>
              <strong>Upload CSV</strong> adds new request IDs and updates an ID that is already stored. The desk then
              analyses the file again. A file you downloaded can be uploaded straight back.
            </li>
          </ol>
          <figure>
            <img src="/guide/upload.png" alt="The upload window, with a place to drop a CSV file." />
            <figcaption>Drop a CSV on the upload window, or choose a file, then select Upload and analyse.</figcaption>
          </figure>
        </section>
      </article>
    </main>
  );
}
