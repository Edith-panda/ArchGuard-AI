import { useRef, useState } from "react";
import ArchitectureGraph
  from "./ArchitectureGraph";



const SUPPORTED_EXTENSIONS = [
  ".json",
  ".yaml",
  ".yml",
  ".tf",
  ".hcl",

  ".py",
  ".java",
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".go",

  ".properties",
  ".toml",
  ".xml",

  ".md",
  ".txt",

  ".proto",

  ".png",
  ".jpg",
  ".jpeg",
  ".webp",

  ".pdf",

  ".zip",
];


function getExtension(fileName) {
  const lowerName =
    fileName.toLowerCase();

  if (lowerName === "dockerfile") {
    return "dockerfile";
  }

  const dotIndex =
    lowerName.lastIndexOf(".");

  if (dotIndex === -1) {
    return "";
  }

  return lowerName.slice(
    dotIndex
  );
}


function formatFileSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(
      bytes / 1024
    ).toFixed(1)} KB`;
  }

  return `${(
    bytes /
    (1024 * 1024)
  ).toFixed(1)} MB`;
}

// const [result, setResult] =
//   useState(null);
//   setResult(data);



function FileDropZone({
  files,
  setFiles,
}) {
  const inputRef =
    useRef(null);

  const [dragging, setDragging] =
    useState(false);

  const [fileError, setFileError] =
    useState("");


  function isSupported(file) {
    const extension =
      getExtension(file.name);

    return (
      SUPPORTED_EXTENSIONS.includes(
        extension
      ) ||
      extension === "dockerfile"
    );
  }


  function addFiles(fileList) {
    setFileError("");

    const incomingFiles =
      Array.from(fileList);

    const unsupported =
      incomingFiles.filter(
        (file) =>
          !isSupported(file)
      );

    if (unsupported.length > 0) {
      setFileError(
        `Unsupported file: ${
          unsupported[0].name
        }`
      );
    }

    const supported =
      incomingFiles.filter(
        isSupported
      );

    setFiles(
      (currentFiles) => {
        const existingKeys =
          new Set(
            currentFiles.map(
              (file) =>
                `${file.name}-${file.size}`
            )
          );

        const uniqueNewFiles =
          supported.filter(
            (file) =>
              !existingKeys.has(
                `${file.name}-${file.size}`
              )
          );

        return [
          ...currentFiles,
          ...uniqueNewFiles,
        ];
      }
    );
  }


  function handleDrop(event) {
    event.preventDefault();

    setDragging(false);

    addFiles(
      event.dataTransfer.files
    );
  }


  function removeFile(index) {
    setFiles(
      (currentFiles) =>
        currentFiles.filter(
          (_, fileIndex) =>
            fileIndex !== index
        )
    );
  }


  return (
    <div>

      <div
        className={
          `drop-zone ${
            dragging
              ? "dragging"
              : ""
          }`
        }
        onClick={() =>
          inputRef.current?.click()
        }
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragging(false);
        }}
        onDrop={handleDrop}
      >

        <div className="upload-icon">
          ↑
        </div>

        <h3>
          Drop architecture files here
        </h3>

        <p>
          or click to browse your
          computer
        </p>

        <div className=
          "supported-types"
        >
          JSON • YAML • Terraform •
          Kubernetes • OpenAPI • Source
          Code • Docs • Diagrams
        </div>

        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={(event) =>
            addFiles(
              event.target.files
            )
          }
        />

      </div>


      {fileError && (
        <div className="error-box">
          {fileError}
        </div>
      )}


      {files.length > 0 && (
        <div className=
          "selected-files"
        >

          <div className=
            "file-summary"
          >
            <strong>
              {files.length}
            </strong>
            {" "}
            artifact
            {files.length !== 1
              ? "s"
              : ""}
            {" "}
            ready for analysis
          </div>


          {files.map(
            (file, index) => (

              <div
                className="file-card"
                key={
                  `${file.name}-${file.size}`
                }
              >

                <div className=
                  "file-info"
                >
                  <div className=
                    "file-status"
                  >
                    ✓
                  </div>

                  <div>
                    <strong>
                      {file.name}
                    </strong>

                    <span>
                      {
                        formatFileSize(
                          file.size
                        )
                      }
                    </span>
                  </div>
                </div>


                <button
                  type="button"
                  className=
                    "remove-file"
                  onClick={(
                    event
                  ) => {
                    event.stopPropagation();

                    removeFile(
                      index
                    );
                  }}
                >
                  ×
                </button>

              </div>

            )
          )}

        </div>
      )}

    </div>
  );
}


export default FileDropZone;