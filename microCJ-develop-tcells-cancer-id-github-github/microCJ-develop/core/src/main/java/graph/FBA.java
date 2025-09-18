package graph;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;
public class FBA {
    public static Map<String, String> loadFBA(String fileName) {
        Map<String, String> dataMap = new HashMap<>();
        String filePath = "C:/oncologyphd/microCJ-develop-tcells-cancer-id/microCJ-develop/core/src/main/resources/" + fileName + ".tsv";

        try (BufferedReader bufferedReader = new BufferedReader(new FileReader(filePath))) {
            // Skip the header line
            bufferedReader.readLine();

            String currentLine;
            while ((currentLine = bufferedReader.readLine()) != null) {
                String[] columns = currentLine.split("\t");
                if (columns.length >= 2) {
                    // Directly insert the key-value pair into the map
                    dataMap.put(columns[0], columns[1]);
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return dataMap;
    }
    public static List<String> getCellId(Map<String, String> data) {
        // Directly convert the keySet to a list
        return new ArrayList<>(data.keySet());
    }

}
