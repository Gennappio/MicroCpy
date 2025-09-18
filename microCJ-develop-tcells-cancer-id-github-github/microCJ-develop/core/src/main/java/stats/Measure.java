/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package stats;

import java.util.Map;

/**
 * Class that represents a single measure taken, with a header and a value. In case of complex measures (having several columns)
 * the header and the value will be expressed as CSV.
 * @author Pedro Victori
 */
class Measure {
	private final String header;
	private final String value;

	/**
	 * Creates a new instance with the specified header and value
	 * @param header the header for this measure
	 * @param value the value for this measure
	 */
	Measure(String header, String value) {
		this.header = header;
		this.value = value;
	}

	/**
	 * Creates a new instance with the specified complex header and value, and stores them as CSV
	 * @param map A map where each column header is a key.
	 */
	Measure(Map<String, Integer> map) {
		this(map, "", "");
	}

	/**
	 * Creates a new instance with the specified complex header and value, and stores them as CSV
	 * @param map A map where each column header is a key.
	 * @param headerPrefix a prefix to write before each column header
	 * @param headerSuffix a suffix to write after each column header
	 */
	Measure(Map<String, Integer> map, String headerPrefix, String headerSuffix) {
		String[] headerArray = new String[map.size()];
		String[] valueArray = new String[map.size()];

		int i = 0;
		for (String key : map.keySet()) {
			headerArray[i] = headerPrefix + key + headerSuffix;
			valueArray[i] = Integer.toString(map.get(key));
			i++;
		}

		this.header = String.join(",",headerArray);
		this.value = String.join(",",valueArray); //arrays to csv
	}

	String getHeader() {
		return header;
	}

	String getValue() {
		return value;
	}
}
