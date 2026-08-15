import { h, V as Ve, l as z, _, S as Se, i as ie } from './src3-5rjOoBTa.js';
import './async-Cv1-GZGV.js';
import { d as attr } from './renderer-B44-mkIR.js';

function s(s,c){s.component(s=>{let{value:l,display_mode:u=`solid`,clear_color:d=[0,0,0,0],label:f=``,show_label:p,i18n:m,zoom_speed:h$1=1,pan_speed:g=1,camera_position:_$1=[null,null,null],has_change_history:v=false}=c;h(s,{show_label:p,Icon:z,label:f||m(`3D_model.3d_model`)}),s.push(`<!----> `),l?(s.push(`<!--[-->`),s.push(`<div class="model3D svelte-pnaihf" data-testid="model3d">`),Ve(s,{children:e=>{e.push(`<!--[-->`),_(e,{Icon:Se,label:`Undo`,onclick:()=>void 0,disabled:!v}),e.push(`<!--]--> <a${attr(`href`,l.url)}${attr(`target`,window.__is_colab__?`_blank`:null)}${attr(`download`,window.__is_colab__?null:l.orig_name||l.path)} data-testid="model3d-download-link">`),_(e,{Icon:ie,label:m(`common.download`)}),e.push(`<!----></a>`);}}),s.push(`<!----> `),s.push(`<!--[!-->`),s.push(`<!---->`),(void 0)(s,{value:l,display_mode:u,clear_color:d,camera_position:_$1,zoom_speed:h$1,pan_speed:g}),s.push(`<!---->`),s.push(`<!--]--></div>`)):s.push(`<!--[!-->`),s.push(`<!--]-->`);});}

export { s };
//# sourceMappingURL=Model3D-DvSwgHWS.js.map
