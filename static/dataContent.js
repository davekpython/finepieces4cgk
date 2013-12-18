var tableContent = ""

for p in posts {
	tableContent += "<td>" + <img src= "/download-art-objects/{{p.key()}}" alt="DgK Cafe" class="objectsfront2"> + "</td>";
	}
output.innerHTML = tableContent;