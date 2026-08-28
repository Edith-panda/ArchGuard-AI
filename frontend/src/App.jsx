import { useMemo, useState } from "react";

import {
  Background,
  Controls,
  ReactFlow,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";
import "./App.css";

import FileDropZone from "./components/FileDropZone";


const SAMPLE_ARCHITECTURE = {
  services: [
    {
      name: "API Gateway",
      type: "gateway",
    },
    {
      name: "Order Service",
      type: "microservice",
    },
    {
      name: "Payment Service",
      type: "microservice",
    },
    {
      name: "PostgreSQL",
      type: "database",
    },
  ],

  connections: [
    ["API Gateway", "Order Service"],
    ["Order Service", "Payment Service"],
    ["Order Service", "PostgreSQL"],
    ["Payment Service", "PostgreSQL"],
  ],
};


function App() {
  const [architectureText, setArchitectureText] =
    useState("");

  const [architecture, setArchitecture] =
    useState(SAMPLE_ARCHITECTURE);

  const [analysis, setAnalysis] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [files, setFiles] =
    useState([]);

  const [
    showManualInput,
    setShowManualInput,
  ] = useState(false);


  const nodes = useMemo(() => {
    return architecture.services.map(
      (service, index) => ({
        id: service.name,

        data: {
          label:
            `${service.name}\n(${service.type})`,
        },

        position: {
          x: (index % 2) * 300,
          y:
            Math.floor(index / 2)
            * 180,
        },
      })
    );
  }, [architecture]);


  const edges = useMemo(() => {
    return architecture.connections.map(
      (
        [source, destination],
        index
      ) => ({
        id: `edge-${index}`,
        source,
        target: destination,
        animated: true,
      })
    );
  }, [architecture]);


 async function analyzeArchitecture() {
  setLoading(true);
  setError("");

  const hasFiles =
    files.length > 0;

  const hasManualInput =
    architectureText
      .trim()
      .length > 0;

  if (
    !hasFiles &&
    !hasManualInput
  ) {
    setError(
      "Please upload at least one file or paste architecture content."
    );

    setLoading(false);

    return;
  }

  try {

    /*
     * STEP 1
     *
     * Send every artifact to the
     * ArchGuard ingestion pipeline.
     */

    const formData =
      new FormData();

    files.forEach((file) => {
      formData.append(
        "files",
        file
      );
    });

    if (hasManualInput) {
      formData.append(
        "manual_input",
        architectureText
      );
    }


    const ingestResponse =
      await fetch(
        "http://127.0.0.1:8000/ingest",
        {
          method: "POST",
          body: formData,
        }
      );


    const ingestResult =
      await ingestResponse.json();


    if (!ingestResponse.ok) {
      throw new Error(
        ingestResult.detail ||
          "Artifact ingestion failed."
      );
    }


    /*
     * STEP 2
     *
     * Check whether the ingestion
     * pipeline reconstructed a canonical
     * architecture.
     */

    if (
      !ingestResult
        .architecture_detected
    ) {
      throw new Error(
        "The files were uploaded successfully, but ArchGuard could not yet reconstruct an architecture from these artifact types. JSON architecture detection works now; Terraform, Kubernetes, source-code and documentation extraction are added in the next parser stage."
      );
    }


    const reconstructedArchitecture =
      ingestResult.architecture;


    setArchitecture(
      reconstructedArchitecture
    );


    /*
     * STEP 3
     *
     * Pass the reconstructed architecture
     * through our existing analysis
     * pipeline.
     */

    const analysisResponse =
      await fetch(
        "http://127.0.0.1:8000/analyze",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify(
            reconstructedArchitecture
          ),
        }
      );


    const analysisResult =
      await analysisResponse.json();


    if (!analysisResponse.ok) {
      throw new Error(
        analysisResult.detail ||
          "Architecture analysis failed."
      );
    }


    setAnalysis(
      analysisResult
    );

  } catch (err) {

    setError(
      err.message ||
        "Something went wrong."
    );

  } finally {

    setLoading(false);

  }
}

  return (
    <div className="app-shell">

      <header className="hero">

        <div>
          <p className="eyebrow">
            AI ARCHITECTURE ENGINEER
          </p>

          <h1>
            ArchGuard AI
          </h1>

          <p className="hero-copy">
            Reconstruct, analyze and
            stress-test software systems
            using deterministic rules,
            graph intelligence, grounded
            retrieval and Gemini.
          </p>
        </div>

        <div className="status-chip">
          Local Prototype
        </div>

      </header>


      <main>

        <section
          className=
            "panel input-panel"
        >

          <div
            className=
              "section-heading"
          >

            <div>

              <p className="step-label">
                Architecture Input
              </p>

              <h2>
                Analyze your system
              </h2>

              <p className=
                "section-description"
              >
                Upload one or more
                architecture artifacts,
                or paste architecture
                content manually.
              </p>

            </div>

          </div>


          <FileDropZone
            files={files}
            setFiles={setFiles}
          />


          <div
            className=
              "manual-input-toggle"
          >

            <button
              type="button"
              className=
                "secondary-button"
              onClick={() =>
                setShowManualInput(
                  (current) =>
                    !current
                )
              }
            >

              {
                showManualInput
                  ? "Hide manual input"
                  : "Paste manually instead"
              }

            </button>

          </div>


          {showManualInput && (

            <div
              className=
                "manual-input-section"
            >

              <div
                className=
                  "manual-input-header"
              >

                <div>

                  <p
                    className=
                      "paste-label"
                  >
                    Paste architecture
                    manually
                  </p>

                  <p
                    className=
                      "manual-helper"
                  >
                    You can paste an
                    architecture definition
                    here instead of uploading
                    files, or use both
                    together.
                  </p>

                </div>

              </div>


              <textarea
                value={
                  architectureText
                }
                onChange={(event) =>
                  setArchitectureText(
                    event.target.value
                  )
                }
                spellCheck="false"
                placeholder={`Paste architecture JSON here...

Example:

{
  "services": [
    {
      "name": "API Gateway",
      "type": "gateway"
    }
  ],
  "connections": []
}`}
              />

            </div>

          )}


          <div
            className=
              "input-status-row"
          >

            <div
              className=
                "input-status"
            >

              <span>
                Files
              </span>

              <strong>
                {files.length}
              </strong>

            </div>


            <div
              className=
                "input-status"
            >

              <span>
                Manual input
              </span>

              <strong>
                {
                  architectureText
                    .trim()
                    .length > 0
                    ? "Ready"
                    : "Empty"
                }
              </strong>

            </div>

          </div>


          <button
            className=
              "primary-button"
            onClick={
              analyzeArchitecture
            }
            disabled={loading}
          >

            {
              loading
                ? "Analyzing..."
                : "Analyze System"
            }

          </button>


          {error && (
            <div className=
              "error-box"
            >
              {error}
            </div>
          )}

        </section>


        <section className="panel">

          <div
            className=
              "section-heading"
          >

            <div>

              <p className="step-label">
                Architecture Graph
              </p>

              <h2>
                Dependency topology
              </h2>

            </div>


            <span className="metric">
              {
                architecture
                  .services
                  .length
              }{" "}
              components
            </span>

          </div>


          <div
            className=
              "graph-container"
          >

            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
            >
              <Background />
              <Controls />
            </ReactFlow>

          </div>

        </section>


        {analysis && (
          <>

            <section
              className=
                "summary-grid"
            >

              <div
                className=
                  "summary-card"
              >

                <span>
                  Components
                </span>

                <strong>
                  {
                    analysis
                      .architecture
                      .component_count
                  }
                </strong>

              </div>


              <div
                className=
                  "summary-card"
              >

                <span>
                  Connections
                </span>

                <strong>
                  {
                    analysis
                      .architecture
                      .connection_count
                  }
                </strong>

              </div>


              <div
                className=
                  "summary-card"
              >

                <span>
                  Findings
                </span>

                <strong>
                  {
                    analysis
                      .findings
                      .length
                  }
                </strong>

              </div>


              <div
                className=
                  "summary-card"
              >

                <span>
                  Gemini
                </span>

                <strong>
                  {
                    analysis
                      .gemini_available
                      ? "Online"
                      : "Fallback"
                  }
                </strong>

              </div>

            </section>


            <section className="panel">

              <div
                className=
                  "section-heading"
              >

                <div>

                  <p className=
                    "step-label"
                  >
                    Graph Intelligence
                  </p>

                  <h2>
                    Critical Components
                  </h2>

                </div>

              </div>


              <div
                className=
                  "critical-list"
              >

                {
                  analysis
                    .critical_components
                    .map(
                      (
                        component,
                        index
                      ) => (

                        <div
                          className=
                            "critical-row"
                          key={
                            component
                              .component
                          }
                        >

                          <span>
                            {index + 1}.
                            {" "}
                            {
                              component
                                .component
                            }
                          </span>

                          <strong>
                            {
                              component
                                .criticality_score
                            }
                            /100
                          </strong>

                        </div>

                      )
                    )
                }

              </div>

            </section>


            <section className="panel">

              <div
                className=
                  "section-heading"
              >

                <div>

                  <p className=
                    "step-label"
                  >
                    Risk Intelligence
                  </p>

                  <h2>
                    Ranked Findings
                  </h2>

                </div>

              </div>


              <div className="findings">

                {
                  analysis
                    .findings
                    .map(
                      (
                        finding,
                        index
                      ) => (

                        <article
                          className=
                            "finding-card"
                          key={
                            `${finding.source}-${index}`
                          }
                        >

                          <div
                            className=
                              "finding-top"
                          >

                            <span
                              className={
                                `severity ${
                                  finding
                                    .severity
                                    .toLowerCase()
                                }`
                              }
                            >
                              {
                                finding
                                  .severity
                              }
                            </span>


                            <span
                              className=
                                "risk-score"
                            >
                              Risk{" "}
                              {
                                finding
                                  .risk_score
                              }
                              /100
                            </span>

                          </div>


                          <h3>
                            {
                              finding
                                .issue
                            }
                          </h3>


                          <p
                            className=
                              "component"
                          >
                            {
                              finding
                                .component
                            }
                            {" • "}
                            {
                              finding
                                .category
                            }
                          </p>


                          <p>
                            {
                              finding
                                .explanation
                            }
                          </p>


                          <div
                            className=
                              "recommendation"
                          >

                            <strong>
                              Recommendation
                            </strong>

                            <p>
                              {
                                finding
                                  .recommendation
                              }
                            </p>

                          </div>


                          <small>
                            Source:{" "}
                            {
                              finding
                                .source
                            }
                          </small>

                        </article>

                      )
                    )
                }

              </div>

            </section>


            <section className="panel">

              <div
                className=
                  "section-heading"
              >

                <div>

                  <p className=
                    "step-label"
                  >
                    Grounding
                  </p>

                  <h2>
                    Retrieved Knowledge
                  </h2>

                </div>

              </div>


              <div
                className=
                  "knowledge-grid"
              >

                {
                  analysis
                    .knowledge_sources
                    ?.map(
                      (source) => (

                        <article
                          className=
                            "knowledge-card"
                          key={
                            source.id
                          }
                        >

                          <span>
                            {
                              source
                                .category
                            }
                          </span>

                          <h3>
                            {
                              source
                                .title
                            }
                          </h3>

                          <p>
                            {
                              source
                                .content
                            }
                          </p>

                        </article>

                      )
                    )
                }

              </div>

            </section>

          </>
        )}

      </main>

    </div>
  );
}


export default App;