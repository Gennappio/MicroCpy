import com.bpodgursky.jbool_expressions.Expression;
import com.bpodgursky.jbool_expressions.parsers.ExprParser;
import com.bpodgursky.jbool_expressions.rules.RuleSet;

import java.util.HashMap;
import java.util.Map;

class RuleTester {
	public static void main(String[] args) {
		String test = "(RAS or PKC) and not (ERK or AKT)";
		System.out.println("1: " + test);

		//replace all operators with boolean symbols
		test = test.replace("and", "&")
			.replace("or", "|")
			.replace("not", "!");

		System.out.println("2: " + test);

		Expression<String> parsedExpression = RuleSet.simplify(ExprParser.parse(test));

		System.out.println("3: " + parsedExpression);

		//build assignments
		Map<String, Boolean> values = new HashMap<>();
		values.put("RAS", false);
		values.put("PKC", true);
		values.put("ERK", false);
		values.put("AKT", false);

		//checking it works when variables not present in the expression are assigned
		values.put("RARSTS", false);
		values.put("PRSTKC", true);
		values.put("ERCDXK", false);
		values.put("AKWFT", false);

		Expression<String> resolved = RuleSet.assign(parsedExpression, values);
		boolean bool = Boolean.parseBoolean(resolved.toString());
		System.out.println("4: " + bool);

	}
}
