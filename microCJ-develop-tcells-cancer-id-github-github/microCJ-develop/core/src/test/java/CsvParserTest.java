import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.io.Reader;

/**
 * @author Pedro Victori
 */
/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
class CsvParserTest {
	public static void main(String[] args) {
		Reader in = null;
		try {
			in = new FileReader(CsvParserTest.class.getClassLoader().getResource("mutations.csv").getPath());
		} catch (FileNotFoundException e) {
			e.printStackTrace();
		}
		CSVParser records = null;
		try {
			records = CSVFormat.EXCEL.withFirstRecordAsHeader().parse(in);
		} catch (IOException e) {
			e.printStackTrace();
		}
		System.out.println(records.getHeaderMap().keySet().toString());
		for (CSVRecord record : records) {
			System.out.println(record.size());
			System.out.println(record.get(0));
			System.out.println(record.get(1));
			System.out.println(record.get(2));
			System.out.println(record.get(3));

		}
	}
}
