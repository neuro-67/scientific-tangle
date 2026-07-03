import cytoscape from "cytoscape";
function bg(color) {
  const cy = cytoscape({
    headless: true, styleEnabled: true,
    elements: [{ data: { id: "n1", type: "Material" } }],
    style: [
      { selector: "node", style: { "background-color": "#888888" } },
      { selector: 'node[type = "Material"]', style: { "background-color": color } },
    ],
  });
  return cy.$("#n1").style("background-color");
}
console.log("space  hsl(190 90% 42%)   =>", bg("hsl(190 90% 42%)"));
console.log("comma  hsl(190, 90%, 42%) =>", bg("hsl(190, 90%, 42%)"));
console.log("grey base #888888         =>", bg("#888888"));
