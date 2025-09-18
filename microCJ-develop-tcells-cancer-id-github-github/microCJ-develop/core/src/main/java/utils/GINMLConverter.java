package utils;

import core.Fate;
import net.lingala.zip4j.ZipFile;
import net.lingala.zip4j.model.FileHeader;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.StringJoiner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;


public class GINMLConverter {
	static int edgeId = 0;
	private static final String header = """
			<?xml version="1.0" encoding="UTF-8"?><graphml xmlns="http://graphml.graphdrawing.org/xmlns">
			<key attr.name="label" attr.type="string" for="node" id="label"/>
			<key attr.name="weight" attr.type="double" for="edge" id="weight"/>
			<key attr.name="kind" attr.type="string" for="node" id="kind"/>
			<key attr.name="rule" attr.type="string" for="node" id="rule"/>
			<key attr.name="value" attr.type="string" for="node" id="value"/>
			<key attr.name="sign" attr.type="string" for="edge" id="sign"/>
			<graph edgedefault="directed">""";

	public static void run(String src) throws IOException {
		//String dest = src.split(".ginml")[0] + ".graphml";
		String dest = src.split(".zginml")[0] + ".graphml";
		ZipFile zipFile = new ZipFile(src);
		System.out.println(zipFile);
		FileHeader fileHeader = zipFile.getFileHeader("GINsim-data/regulatoryGraph.ginml");
		InputStream inputStream = zipFile.getInputStream(fileHeader);
		var reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8));
		//File ginmlFile = new File("GINsim-data/regulatoryGraph.ginml");
		//System.out.println("Absolute path of ginml file: " + ginmlFile.getAbsolutePath());
		//var reader = new BufferedReader(new FileReader(src, StandardCharsets.UTF_8));
		StringJoiner sj = new StringJoiner(System.lineSeparator());
		sj.add(header);

		String line;
		boolean rule = false;
		String id = null;
		while ((line = reader.readLine()) != null) {
			line = line.strip();
			if (line.startsWith("<node id=")) { //start of node element
				id = line.split("\"")[1];
				String label = id.replace("\"", "");
				String node = "<node id=\"" + id + "\">";
				sj.add(node);
				sj.add("<data key=\"label\">" + label + "</data>");

			} else if (line.startsWith("<exp str=")) { //rule for node element
				String expr = line.split("\"")[1];
				if (!expr.equals("")) {
					rule = true;
					expr = expr.replaceAll("&amp;", "and");
					expr = expr.replaceAll("\\|", "or");
					expr = expr.replaceAll("!", "not ");

					String kind = "gene";
					for (Fate fate : Fate.values()) {
						if (Objects.requireNonNull(id).equalsIgnoreCase(fate.toString())) {
							kind = "fate";
							break;
						}
					}
					sj.add("<data key=\"kind\">" + kind + "</data>");
					sj.add("<data key=\"rule\">" + expr + "</data>");
				}

			} else if (line.startsWith("</node>")) { //end of node element
				if (rule) {
					sj.add("<data key=\"value\">1</data>");
				} else {
					sj.add("<data key=\"kind\">input</data>");
				}
				sj.add("</node>");
				rule = false;

			} else if (line.startsWith("<edge id=")) { //edge node
				Pattern p = Pattern.compile("(?<=id=\")([^\"]+).*(?<=from=\")([^\"]+).*(?<=to=\")([^\"]+).*(?<=sign=\")([^\"]+)");
				Matcher m = p.matcher(line);
				String edge = null;
				String from = null;
				String to = null;
				String sign = null;
				while (m.find()) {
					edge = m.group(1);
					from = m.group(2);
					to = m.group(3);
					sign = m.group(4);
				}
				sj.add("<edge id=\"" + edge + "\" source=\"" + from + "\" target=\"" + to + "\">");
				sj.add("<data key=\"weight\">1.0</data>");
				sj.add("<data key=\"sign\">" + sign + "</data>");
				sj.add("</edge>");

			}
		}
		sj.add("</graph>");
		sj.add("</graphml>");
		String graphml = sj.toString();
		var writer = new BufferedWriter(new FileWriter(dest));
		writer.write(graphml);
		writer.close();
	}
}
