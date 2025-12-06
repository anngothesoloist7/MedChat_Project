importScripts('https://cdn.jsdelivr.net/npm/@saehrimnir/druidjs/dist/druid.min.js');

const MESSAGE_INTERVAL = 200;

self.onmessage = function (e) {
  let now = new Date().getTime();
  // Ensure params is a mutable clean object
  const params = e.data.params ? JSON.parse(JSON.stringify(e.data.params)) : {};
  const algorithm = params.algorithm || 'UMAP'; 
  
  // Ensure vectors is mutable
  if (!e.data.vectors || e.data.vectors.length === 0) {
    self.postMessage({ result: [], error: 'No data found' });
    return;
  }
  // Shallow copy of the array is usually enough, unless it modifies inner arrays
  const vectors = [...e.data.vectors];

  try {
    // Initialize Algorithm
    // DruidJS exposes itself as 'druid'
    const AlgorithmClass = druid[algorithm];
    if (!AlgorithmClass) {
        throw new Error(`Algorithm ${algorithm} not found`);
    }

    // Convert config params for Druid
    // UMAP specific mappings if needed (Druid uses standard names usually)
    // Create a mutable copy of params and add Druid-specific mappings
    const algoParams = { 
        ...params,
        local_connectivity: params.nNeighbors || 15,
        min_dist: params.minDist || 0.1,
    };
    
    // Algorithm specific tweaks
    if (algorithm === 'TSNE') {
        algoParams.perplexity = params.perplexity || 30;
    }
    // Remove 'algorithm' from params passed to constructor if it causes issues, though usually fine.
    // The error likely came from '...params' if params itself was frozen, but the spread operator creates a new object.
    // However, if Druid tries to modify 'vectors' (input data) and that's frozen, that's another issue.
    // 'vectors' comes from e.data.vectors.
    
    // Let's also clone the vectors to be safe, though expensive.
    // For now, let's trust the new object creation.
    // Note: The user error "Cannot add property algorithm..." might be happening inside Druid if it tries to modify 'vectors' metadata or similar. 
    // But usually it's the config object.
    
    // Explicitly using a new object for algoParams is correct.

    const D = new AlgorithmClass(vectors, algoParams); 
    const next = D.generator();

    let reducedPoints = [];
    for (reducedPoints of next) {
      if (Date.now() - now > MESSAGE_INTERVAL) {
        now = Date.now();
        self.postMessage({ result: matrixToPoints(reducedPoints), status: 'running' });
      }
    }
    // Final result
    self.postMessage({ result: matrixToPoints(reducedPoints), status: 'complete' });

  } catch (err) {
    self.postMessage({ error: err.message || String(err), status: 'error' });
  }
};

function matrixToPoints(matrix) {
  return matrix.map(p => ({ x: p[0], y: p[1] }));
}
