function SourceList({ sources }) {

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="sources">

      <h4>Sources</h4>

      {sources.map((source, index) => (

        <div
          className="source-card"
          key={index}
        >

          <strong>
            {source.filename ||
              source.document ||
              `Source ${index + 1}`}
          </strong>

          {source.page && (
            <span>
              Page: {source.page}
            </span>
          )}

          {source.text && (
            <p>{source.text}</p>
          )}

        </div>

      ))}

    </div>
  );
}

export default SourceList;