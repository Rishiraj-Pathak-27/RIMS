const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {start:"_app/immutable/entry/start.Bs09q3BI.js",app:"_app/immutable/entry/app.D1RnSpfp.js",imports:["_app/immutable/entry/start.Bs09q3BI.js","_app/immutable/chunks/P_rAG3G9.js","_app/immutable/chunks/C0NAgWyT.js","_app/immutable/chunks/BmkdwP5E.js","_app/immutable/entry/app.D1RnSpfp.js","_app/immutable/chunks/C0NAgWyT.js","_app/immutable/chunks/BmkdwP5E.js","_app/immutable/chunks/DjaDRR0M.js","_app/immutable/chunks/Bq9Tj-av.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-BJ7JNQxI.js')),
			__memo(() => import('./chunks/1-DWFl2SqO.js')),
			__memo(() => import('./chunks/2-PObSCLX9.js').then(function (n) { return n.a0; }))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/[...catchall]",
				pattern: /^(?:\/([^]*))?\/?$/,
				params: [{"name":"catchall","optional":false,"rest":true,"chained":true}],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();

const prerendered = new Set([]);

const base = "";

export { base, manifest, prerendered };
//# sourceMappingURL=manifest.js.map
